FROM python:3.12-slim

LABEL maintainer="bo@symio.ai"
LABEL description="DuelAI Pipeline - Multi-model AI debate consensus engine"

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY setup.py .
COPY duelai/ duelai/
RUN pip install --no-cache-dir -e .

# Config and data
COPY config.json registry.json alerts.json ./
RUN mkdir -p /app/versions

# Ports: 8000 = API, 5050 = Dashboard
EXPOSE 8000 5050

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: run API server
ENV DUELAI_BASE=/app
CMD ["uvicorn", "duelai.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
