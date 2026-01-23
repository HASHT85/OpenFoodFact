.PHONY: help build up down restart logs clean test etl-full etl-skip shell mysql-shell

# Default target
help:
	@echo "OpenFoodFacts ETL - Docker Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup & Management:"
	@echo "  make build         Build all Docker images"
	@echo "  make up            Start all services"
	@echo "  make down          Stop all services"
	@echo "  make restart       Restart all services"
	@echo "  make logs          Show logs (all services)"
	@echo "  make clean         Clean all data and volumes"
	@echo ""
	@echo "ETL Operations:"
	@echo "  make etl-test      Run ETL with test data"
	@echo "  make etl-full      Run full ETL pipeline (requires data file)"
	@echo "  make etl-skip      Run ETL skipping ingestion (use existing Bronze)"
	@echo "  make download      Download OpenFoodFacts full dataset"
	@echo ""
	@echo "Development:"
	@echo "  make shell         Open shell in ETL container"
	@echo "  make mysql-shell   Open MySQL shell"
	@echo "  make jupyter       Start Jupyter Lab"
	@echo "  make test          Run unit tests"
	@echo ""
	@echo "Utilities:"
	@echo "  make ps            Show running containers"
	@echo "  make logs-etl      Show ETL logs only"
	@echo "  make logs-mysql    Show MySQL logs only"

# Build images
build:
	docker-compose build

# Start services
up:
	docker-compose up -d
	@echo "Waiting for MySQL to be ready..."
	@sleep 10
	@echo "Services started! Use 'make logs' to see logs."

# Stop services
down:
	docker-compose down

# Restart services
restart:
	docker-compose restart

# Show logs
logs:
	docker-compose logs -f

logs-etl:
	docker-compose logs -f etl

logs-mysql:
	docker-compose logs -f mysql

# Show running containers
ps:
	docker-compose ps

# Clean everything (WARNING: deletes data)
clean:
	@echo "WARNING: This will delete all data volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		rm -rf data/bronze data/silver data/gold data/quality_reports data/*.jsonl; \
		echo "Cleaned successfully!"; \
	fi

# ETL Operations
etl-test:
	docker-compose exec etl python -m etl.main tests/sample_data.jsonl

etl-full:
	@if [ ! -f "data/openfoodfacts-products.jsonl" ]; then \
		echo "Error: data/openfoodfacts-products.jsonl not found!"; \
		echo "Run 'make download' first to download the dataset."; \
		exit 1; \
	fi
	docker-compose exec etl python -m etl.main data/openfoodfacts-products.jsonl

etl-skip:
	docker-compose exec etl python -m etl.main --skip-ingest

# Download OpenFoodFacts dataset
download:
	docker-compose exec etl python download_dump.py

# Development tools
shell:
	docker-compose exec etl bash

mysql-shell:
	docker-compose exec mysql mysql -u root -ppassword off_datamart

# Run tests
test:
	docker-compose exec etl pytest tests/test_etl.py -v

test-coverage:
	docker-compose exec etl pytest tests/test_etl.py --cov=etl --cov-report=html

# Quality report
quality-report:
	docker-compose exec etl python -m etl.jobs.quality_report

# Run individual ETL jobs
job-ingest:
	docker-compose exec etl python -m etl.jobs.ingest tests/sample_data.jsonl

job-conform:
	docker-compose exec etl python -m etl.jobs.conform

job-load-dims:
	docker-compose exec etl python -m etl.jobs.load_dimensions

job-load-product:
	docker-compose exec etl python -m etl.jobs.load_product_scd

job-load-fact:
	docker-compose exec etl python -m etl.jobs.load_fact

# SQL queries
sql-analysis:
	docker-compose exec mysql mysql -u root -ppassword off_datamart < sql/analysis_queries.sql
