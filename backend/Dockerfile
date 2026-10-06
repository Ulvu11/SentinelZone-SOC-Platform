FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt \
    && groupadd --system --gid 10001 sentinelzone \
    && useradd --system --uid 10001 --gid sentinelzone --create-home --home-dir /var/lib/sentinelzone sentinelzone
COPY --chown=sentinelzone:sentinelzone . .
USER sentinelzone
EXPOSE 8003
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8003 --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1}"]
