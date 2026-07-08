# Build context is the REPOSITORY ROOT (not operator/), because the operator
# depends on the local orchestra-template-tools package (#51). Build with:
#   docker buildx build -f operator/Dockerfile <repo-root>
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# The local path dependency must exist before `uv sync`. operator/pyproject.toml
# references it as ../template-tools, so relative to /app that is /template-tools.
COPY template-tools/ /template-tools/

# Copy requirements first for better caching
COPY operator/pyproject.toml operator/uv.lock ./
RUN pip install uv && uv sync --frozen

# Copy source code. chmod so the files are world-readable regardless of the
# build host's umask — a restrictive umask (e.g. 0027) otherwise bakes in
# root-only files that the non-root runtime user cannot read.
COPY operator/src/ ./src/
RUN chmod -R a+rX /app/src /template-tools

# Set Python path to include the virtual environment
ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

# Run the operator
CMD ["python", "-m", "main"]
