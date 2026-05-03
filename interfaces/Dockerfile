FROM python:3.12-slim

WORKDIR /app

# Dépendances système minimales (httpx async)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python avant de copier le code
# (couche cachée si seul le code change)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Code source
COPY interfaces/ ./interfaces/
COPY core/ ./core/
COPY config/ ./config/

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8100/health || exit 1

CMD ["uvicorn", "interfaces.gateway.gateway:app", \
     "--host", "0.0.0.0", \
     "--port", "8100", \
     "--workers", "2", \
     "--log-level", "info"]
