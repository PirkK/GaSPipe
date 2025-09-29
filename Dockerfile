FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV RC_CLI_PATH=/usr/local/bin/RealityCapture \
    POSTSHOT_CLI_PATH=/usr/local/bin/postshot-cli \
    WORKDIR=/data \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create data directory
RUN mkdir -p /data

# Set working directory for pipeline execution
WORKDIR /data

# Entry point
ENTRYPOINT ["python", "-m", "src.gaspipe.cli"]
CMD ["--help"]