# ADAPT-Data Docker Image
# Production-ready containerized telemetry generation platform

FROM python:3.11-slim

# Set metadata
LABEL maintainer="ADAPT Team"
LABEL description="ADAPT-Data: Synthetic Telemetry & Incident Dataset Generator"
LABEL version="0.4.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt setup.py pyproject.toml ./
COPY generator/__init__.py ./generator/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Create directories for user data
RUN mkdir -p /data/scenarios /data/output /data/plugins \
    && chmod -R 777 /data

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    ADAPT_OUTPUT_DIR=/data/output \
    ADAPT_LOG_LEVEL=INFO

# Create non-root user
RUN useradd -m -u 1000 adapt && \
    chown -R adapt:adapt /app /data

USER adapt

# Set default command
ENTRYPOINT ["adapt-data"]
CMD ["--help"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD adapt-data version || exit 1

# Volume for persistent data
VOLUME ["/data"]

# Expose Prometheus metrics port
EXPOSE 9090

# Example usage:
# docker build -t adapt-data:0.4.0 .
# docker run -v $(pwd)/output:/data/output adapt-data:0.4.0 generate --scenario latency --duration 1h
# docker run -p 9090:9090 -v $(pwd)/output:/data/output adapt-data:0.4.0 serve /data/output
