FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Configure Poetry (don't create venv since we're in container)
RUN poetry config virtualenvs.create false

# Copy source code and README first
COPY src/ ./src/
COPY README.md ./

# Install all dependencies including the current project
RUN poetry install --only=main

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set Python path and entrypoint
ENV PYTHONPATH=/app/src
ENTRYPOINT ["python", "-m", "callie.core.cli"] 