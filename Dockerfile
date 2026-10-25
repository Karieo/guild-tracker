# python:3.12-slim is multi-arch (amd64 + arm64), so this builds natively on bastion.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home app && mkdir -p /data && chown app /data
USER app

ENV DATABASE_PATH=/data/guild.db
EXPOSE 8000
# One worker: SQLite is happiest with a single writer process; threads cover concurrency.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "wsgi:app"]
