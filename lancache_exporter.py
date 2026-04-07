#!/usr/bin/env python3
"""
LanCache / DeveLanCacheUI Prometheus Exporter
Scrapes the DeveLanCacheUI Backend API and exposes metrics for Prometheus.
"""

import time
import logging
import os
import requests
from prometheus_client import start_http_server, Gauge, Counter, Info, REGISTRY
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
import prometheus_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lancache_exporter")

LANCACHE_API_URL = os.environ.get("LANCACHE_API_URL", "http://192.168.20.100:7301")
SCRAPE_INTERVAL  = int(os.environ.get("SCRAPE_INTERVAL", "30"))
EXPORTER_PORT    = int(os.environ.get("EXPORTER_PORT", "9877"))


class LanCacheCollector:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, path: str, params: dict = None):
        try:
            r = self.session.get(f"{self.base_url}{path}", params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.warning(f"Failed to fetch {path}: {e}")
            return None

    def collect(self):
        # ── Total stats ────────────────────────────────────────────────────────
        total = self._get("/DownloadStats/GetTotalDownloadStats")
        if total:
            g = GaugeMetricFamily(
                "lancache_total_cache_hit_bytes",
                "Total bytes served from cache (hits)",
            )
            g.add_metric([], total.get("totalCacheHitBytes", 0))
            yield g

            g = GaugeMetricFamily(
                "lancache_total_cache_miss_bytes",
                "Total bytes fetched from internet (misses)",
            )
            g.add_metric([], total.get("totalCacheMissBytes", 0))
            yield g

            total_bytes = total.get("totalCacheHitBytes", 0) + total.get("totalCacheMissBytes", 0)
            hit_ratio = (total.get("totalCacheHitBytes", 0) / total_bytes) if total_bytes > 0 else 0
            g = GaugeMetricFamily(
                "lancache_cache_hit_ratio",
                "Cache hit ratio (0-1)",
            )
            g.add_metric([], hit_ratio)
            yield g

        # ── Per-service stats ──────────────────────────────────────────────────
        per_service = self._get("/DownloadStats/GetDownloadStatsPerService")
        if per_service:
            hit_fam = GaugeMetricFamily(
                "lancache_service_cache_hit_bytes",
                "Bytes served from cache per service",
                labels=["service"],
            )
            miss_fam = GaugeMetricFamily(
                "lancache_service_cache_miss_bytes",
                "Bytes fetched from internet per service",
                labels=["service"],
            )
            ratio_fam = GaugeMetricFamily(
                "lancache_service_cache_hit_ratio",
                "Cache hit ratio per service (0-1)",
                labels=["service"],
            )
            for svc in per_service:
                name = svc.get("identifier", "unknown")
                hits  = svc.get("totalCacheHitBytes", 0)
                misses = svc.get("totalCacheMissBytes", 0)
                total_b = hits + misses
                ratio = (hits / total_b) if total_b > 0 else 0
                hit_fam.add_metric([name], hits)
                miss_fam.add_metric([name], misses)
                ratio_fam.add_metric([name], ratio)
            yield hit_fam
            yield miss_fam
            yield ratio_fam

        # ── Per-client stats ───────────────────────────────────────────────────
        per_client = self._get("/DownloadStats/GetDownloadStatsPerClient")
        if per_client:
            hit_fam = GaugeMetricFamily(
                "lancache_client_cache_hit_bytes",
                "Bytes served from cache per client IP",
                labels=["client_ip"],
            )
            miss_fam = GaugeMetricFamily(
                "lancache_client_cache_miss_bytes",
                "Bytes fetched from internet per client IP",
                labels=["client_ip"],
            )
            for client in per_client:
                ip = client.get("identifier", "unknown")
                hit_fam.add_metric([ip], client.get("totalCacheHitBytes", 0))
                miss_fam.add_metric([ip], client.get("totalCacheMissBytes", 0))
            yield hit_fam
            yield miss_fam

        # ── Recent download events (last 100) ─────────────────────────────────
        events = self._get("/DownloadEvents/GetBySkipAndCount", {"skip": 0, "count": 100})
        if events:
            event_count = GaugeMetricFamily(
                "lancache_recent_download_events_total",
                "Number of download events in the last 100 fetched",
            )
            event_count.add_metric([], len(events))
            yield event_count

            # Active events = updated in last 60s
            now = time.time()
            active = 0
            for ev in events:
                try:
                    from datetime import datetime, timezone
                    updated = ev.get("lastUpdatedAt", "")
                    if updated:
                        dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        age = now - dt.timestamp()
                        if age < 60:
                            active += 1
                except Exception:
                    pass
            g = GaugeMetricFamily(
                "lancache_active_downloads",
                "Download events updated in the last 60 seconds",
            )
            g.add_metric([], active)
            yield g

        # ── Status / uptime ───────────────────────────────────────────────────
        status = self._get("/Status")
        if status:
            info = GaugeMetricFamily(
                "lancache_up",
                "DeveLanCacheUI backend is reachable (1 = yes)",
            )
            info.add_metric([], 1)
            yield info

            # Expose version as a labelled gauge (standard pattern)
            ver = GaugeMetricFamily(
                "lancache_info",
                "DeveLanCacheUI build info",
                labels=["version", "steam_depot_version"],
            )
            ver.add_metric(
                [
                    status.get("version", "unknown"),
                    status.get("steamDepotVersion", "unknown"),
                ],
                1,
            )
            yield ver
        else:
            g = GaugeMetricFamily("lancache_up", "DeveLanCacheUI backend is reachable (1 = yes)")
            g.add_metric([], 0)
            yield g


def main():
    log.info(f"LanCache Exporter starting — API: {LANCACHE_API_URL}  port: {EXPORTER_PORT}")

    # Disable default process/python metrics to keep it clean (optional)
    # prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)

    collector = LanCacheCollector(LANCACHE_API_URL)
    REGISTRY.register(collector)

    start_http_server(EXPORTER_PORT)
    log.info(f"Metrics available at http://0.0.0.0:{EXPORTER_PORT}/metrics")

    while True:
        time.sleep(SCRAPE_INTERVAL)


if __name__ == "__main__":
    main()
