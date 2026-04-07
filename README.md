# LanCache Prometheus Exporter

Scrapes the **DeveLanCacheUI Backend API** and exposes metrics for Prometheus/Grafana.

---

## Metrics Exposed

| Metric | Labels | Description |
|---|---|---|
| `lancache_up` | — | 1 if API is reachable |
| `lancache_info` | `version`, `steam_depot_version` | Build info |
| `lancache_cache_hit_ratio` | — | Overall hit ratio (0–1) |
| `lancache_total_cache_hit_bytes` | — | All-time cache hit bytes |
| `lancache_total_cache_miss_bytes` | — | All-time cache miss bytes |
| `lancache_service_cache_hit_bytes` | `service` | Hit bytes per service (Steam, Epic, etc.) |
| `lancache_service_cache_miss_bytes` | `service` | Miss bytes per service |
| `lancache_service_cache_hit_ratio` | `service` | Hit ratio per service |
| `lancache_client_cache_hit_bytes` | `client_ip` | Hit bytes per client |
| `lancache_client_cache_miss_bytes` | `client_ip` | Miss bytes per client |
| `lancache_active_downloads` | — | Events updated in last 60s |
| `lancache_recent_download_events_total` | — | Count of last 100 events fetched |

---

## Setup

### Option A — Docker Compose (recommended)

```bash
# If you don't have an external 'monitoring' network yet:
docker network create monitoring

docker compose up -d
```

Edit `docker-compose.yml` to change the `LANCACHE_API_URL` if needed.

### Option B — Run directly with Python

```bash
pip install -r requirements.txt

LANCACHE_API_URL=http://192.168.20.100:7301 python lancache_exporter.py
```

Metrics will be available at: `http://<your-host>:9877/metrics`

---

## Prometheus Config

Add this job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "lancache"
    static_configs:
      - targets: ["<exporter-host>:9877"]
    scrape_interval: 30s
```

---

## Grafana Dashboard

1. In Grafana, go to **Dashboards → Import**
2. Upload `grafana_dashboard.json`
3. Select your Prometheus datasource
4. Click **Import**

The dashboard includes:
- Status / hit ratio / active download stat panels
- Hit vs miss rate over time (timeseries)
- Per-service pie charts (hits & misses)
- Per-service timeseries
- Per-client table (sorted by hit bytes)
- Per-client hit ratio timeseries

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LANCACHE_API_URL` | `http://192.168.20.100:7301` | DeveLanCacheUI backend URL |
| `SCRAPE_INTERVAL` | `30` | Seconds between scrapes |
| `EXPORTER_PORT` | `9877` | Port to expose `/metrics` on |
