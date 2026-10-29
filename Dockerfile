FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KALKAN_HOST=0.0.0.0 \
    KALKAN_PORT=8080 \
    KALKAN_PROVIDER=auto \
    KALKAN_SCREEN=auto

COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
COPY policy ./policy
COPY dashboard ./dashboard
COPY evals ./evals
COPY fixtures ./fixtures
COPY sandbox_data ./sandbox_data

RUN pip install --no-cache-dir .

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health')"

CMD ["kalkan", "serve", "--host", "0.0.0.0", "--port", "8080"]
