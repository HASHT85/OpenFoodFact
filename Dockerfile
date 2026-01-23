FROM python:3.10-slim-bookworm

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
        openjdk-17-jre-headless \
        procps \
        curl \
        wget \
        default-mysql-client \
        bash \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY etl/ ./etl/
COPY sql/ ./sql/
COPY conf/ ./conf/
COPY tests/ ./tests/
COPY download_dump.py ./
COPY entrypoint.sh /entrypoint.sh

# Make entrypoint executable
RUN chmod +x /entrypoint.sh

# Create data directories
RUN mkdir -p /app/data/bronze /app/data/silver /app/data/gold /app/data/quality_reports

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["tail", "-f", "/dev/null"]
