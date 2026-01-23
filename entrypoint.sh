#!/bin/bash
set -e

echo "========================================"
echo "OpenFoodFacts ETL - Starting..."
echo "========================================"

# Wait for MySQL to be ready
echo "Waiting for MySQL at ${DB_HOST}:${DB_PORT}..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if mysql -h"${DB_HOST}" -P"${DB_PORT}" -u"${DB_USER}" -p"${DB_PASSWORD}" -e "SELECT 1" > /dev/null 2>&1; then
        echo "MySQL is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo "Attempt $attempt/$max_attempts - MySQL not ready yet..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "ERROR: MySQL did not become ready in time!"
    exit 1
fi

# Create required directories
mkdir -p /app/data/bronze /app/data/silver /app/data/gold /app/data/quality_reports

echo "========================================"
echo "Environment ready!"
echo "========================================"
echo "Database: ${DB_NAME} @ ${DB_HOST}:${DB_PORT}"
echo "Spark Driver Memory: ${SPARK_DRIVER_MEMORY:-2g}"
echo "========================================"

# Execute the command passed to the container
exec "$@"
