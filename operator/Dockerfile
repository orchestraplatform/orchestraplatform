FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Copy source code. chmod so the files are world-readable regardless of the
# build host's umask — a restrictive umask (e.g. 0027) otherwise bakes in
# root-only files that the non-root runtime user cannot read.
COPY src/ ./src/
RUN chmod -R a+rX /app/src

# Set Python path to include the virtual environment
ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

# Run the operator
CMD ["python", "-m", "main"]
