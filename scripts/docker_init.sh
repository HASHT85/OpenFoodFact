#!/bin/bash
# Initial setup script for Docker environment

set -e

echo "========================================"
echo "OpenFoodFacts ETL - Docker Setup"
echo "========================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed!"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed!"
    echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✓ Docker and Docker Compose are installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo "  Please review and update the values in .env if needed"
else
    echo "✓ .env file already exists"
fi

echo ""

# Create required directories
echo "Creating required directories..."
mkdir -p data/bronze data/silver data/gold data/quality_reports
mkdir -p logs backups
echo "✓ Directories created"

echo ""

# Make scripts executable
echo "Setting script permissions..."
chmod +x entrypoint.sh 2>/dev/null || true
chmod +x scripts/docker_init.sh 2>/dev/null || true
echo "✓ Scripts are executable"

echo ""

# Build Docker images
echo "Building Docker images (this may take a few minutes)..."
docker-compose build

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Review configuration: nano .env"
echo "  2. Start services: make up (or docker-compose up -d)"
echo "  3. Run ETL: make etl-test"
echo ""
echo "For help: make help"
echo "========================================"
