# Build context is the REPOSITORY ROOT (not server/), because the API depends on
# the local orchestra-template-tools package (ADR-0007). Build with:
#   docker buildx build -f server/Dockerfile <repo-root>
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# The local path dependency must exist before `uv sync`. server/pyproject.toml
# references it as ../template-tools, so relative to /app that is /template-tools.
COPY template-tools/ /template-tools/

# Copy requirements first for better caching
COPY server/pyproject.toml server/uv.lock ./
RUN pip install uv && uv sync --frozen && chown -R 1000:1000 /app/.venv

# Copy source code. chmod so the files are world-readable regardless of the
# build host's umask — a restrictive umask (e.g. 0027) otherwise bakes in
# root-only files that the non-root runtime user cannot read.
COPY server/ .
RUN chmod -R a+rX /app /template-tools

# Set Python path to include the virtual environment
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run the API
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
