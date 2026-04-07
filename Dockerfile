FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lancache_exporter.py .

ENV LANCACHE_API_URL=http://192.168.20.100:7301
ENV SCRAPE_INTERVAL=30
ENV EXPORTER_PORT=9877

EXPOSE 9877

CMD ["python", "lancache_exporter.py"]
