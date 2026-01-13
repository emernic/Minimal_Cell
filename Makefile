.PHONY: help build up down logs clean test backend-shell frontend-shell

help:
	@echo "Minimal Cell Model - Development Commands"
	@echo ""
	@echo "  make build          - Build Docker containers"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make logs           - View logs from all services"
	@echo "  make clean          - Remove containers and volumes"
	@echo "  make test           - Run tests (not yet implemented)"
	@echo "  make backend-shell  - Open shell in backend container"
	@echo "  make frontend-shell - Open shell in frontend container"
	@echo ""

build:
	@echo "Building Docker containers..."
	docker-compose build

up:
	@echo "Starting services..."
	docker-compose up -d
	@echo ""
	@echo "Services started!"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend API: http://localhost:8080"
	@echo "  API Docs: http://localhost:8080/docs"
	@echo ""
	@echo "View logs with: make logs"

down:
	@echo "Stopping services..."
	docker-compose down

logs:
	docker-compose logs -f

clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v
	docker system prune -f

test:
	@echo "Running tests..."
	@echo "Tests not yet implemented"

backend-shell:
	docker-compose exec backend /bin/bash

frontend-shell:
	docker-compose exec frontend /bin/sh

# Development shortcuts
dev-backend:
	@echo "Starting backend in development mode..."
	cd backend && python main.py

dev-frontend:
	@echo "Starting frontend in development mode..."
	cd frontend && npm start

install-backend:
	@echo "Installing backend dependencies..."
	pip install -r backend/requirements.txt
	pip install -e odecell/

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
