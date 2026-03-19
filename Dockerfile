# =============================================================================
# Cyphergy — Production Dockerfile
# Multi-stage build | Python 3.11 | Non-root | CPAA-compliant
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install dependencies in a clean layer
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# System dependencies for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy only dependency files first (layer caching)
COPY pyproject.toml ./

# Install project dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies from pyproject.toml
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# Copy the application source
COPY src/ ./src/

# Install the project itself (editable not needed in production)
RUN pip install --no-cache-dir .


# ---------------------------------------------------------------------------
# Stage 2: Runtime — minimal image with only what's needed
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL maintainer="bo@symio.ai"
LABEL description="Cyphergy — AI-powered legal document analysis and motion drafting"

# Runtime system dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
WORKDIR /app
COPY src/ ./src/
COPY pyproject.toml ./

# Create non-root user for security
RUN groupadd --gid 1001 cyphergy && \
    useradd --uid 1001 --gid 1001 --shell /bin/false --create-home cyphergy && \
    chown -R cyphergy:cyphergy /app

USER cyphergy

# CPAA: All configuration comes from environment variables at runtime.
# No secrets, API keys, or provider details are baked into the image.
# Required env vars: see .env.example

# Expose the API port
EXPOSE 8000

# Health check — hits the /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

# Run with uvicorn — production settings
CMD ["uvicorn", "src.api:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--no-access-log"]
