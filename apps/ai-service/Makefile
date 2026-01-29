# EchoTeam AI Service - One-Command Operations
#
# Usage:
#   make start        # Start all services
#   make stop         # Stop all services
#   make restart      # Restart all services
#   make status       # Check service status
#   make logs         # View logs
#   make test         # Run tests

.PHONY: start stop restart status logs test setup help

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[0;33m
NC = \033[0m # No Color

# Services to manage (match actual container names)
SERVICES = echoteam-qdrant echoteam-ollama
AI_SERVICE = ai-service

help:
	@echo "EchoTeam AI Service - Available Commands:"
	@echo ""
	@echo "  make start      - Start all infrastructure services"
	@echo "  make stop       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make status     - Check service status"
	@echo "  make logs       - View service logs"
	@echo "  make test       - Run test suite"
	@echo "  make setup      - Initial setup (install deps, pull models)"
	@echo "  make run        - Run the AI service"
	@echo "  make consumer   - Start the chat processor consumer"

start:
	@echo "$(GREEN)Starting infrastructure services...$(NC)"
	@for service in $(SERVICES); do \
		if ! docker ps --format '{{.Names}}' | grep -q "$$service"; then \
			echo "Starting $$service..."; \
			docker start $$service 2>/dev/null || echo "Container $$service not found, create with:"; \
		else \
			echo "$$service already running"; \
		fi; \
	done
	@echo ""
	@echo "$(GREEN)All services started!$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. make run         - Start the AI service API"
	@echo "  2. make consumer    - Start the chat processor"

stop:
	@echo "$(YELLOW)Stopping infrastructure services...$(NC)"
	@for service in $(SERVICES); do \
		if docker ps --format '{{.Names}}' | grep -q "$$service"; then \
			echo "Stopping $$service..."; \
			docker stop $$service; \
		else \
			echo "$$service not running"; \
		fi; \
	done
	@echo "$(GREEN)All services stopped.$(NC)"

restart: stop start
	@echo "$(GREEN)All services restarted!$(NC)"

status:
	@echo "Service Status:"
	@echo "==============="
	@for service in $(SERVICES); do \
		if docker ps --format '{{.Names}}' | grep -q "$$service"; then \
			echo "$$service: $(GREEN)Running$(NC)"; \
		else \
			echo "$$service: $(RED)Stopped$(NC)"; \
		fi; \
	done
	@echo ""
	@echo "Health Check Endpoints:"
	@echo "  Qdrant:  http://localhost:6333/dashboard"
	@echo "  Ollama:  http://localhost:11434/api/tags"

logs:
	@echo "Showing logs for all services (Ctrl+C to exit):"
	@echo ""
	@for service in $(SERVICES); do \
		if docker ps --format '{{.Names}}' | grep -q "$$service"; then \
			echo "--- $$service ---"; \
			docker logs --tail 20 -f $$service 2>&1 & \
		fi; \
	done
	@wait

setup:
	@echo "$(GREEN)Setting up development environment...$(NC)"
	@echo ""
	@echo "1. Installing Python dependencies..."
	@uv pip install -e ".[dev]" 2>/dev/null || pip install -e ".[dev]"
	@echo ""
	@echo "2. Pulling Ollama models..."
	@ollama pull nomic-embed-text:v1.5 2>/dev/null || echo "Skipping model pull (ollama not running)"
	@echo ""
	@echo "3. Running database initialization..."
	@python scripts/init_db.py 2>/dev/null || echo "No init script found"
	@echo ""
	@echo "$(GREEN)Setup complete!$(NC)"

test:
	@echo "$(GREEN)Running test suite...$(NC)"
	@source .venv/bin/activate && python -m pytest tests/ -v --tb=short 2>&1 | head -100
	@echo ""
	@echo "Test coverage:"
	@source .venv/bin/activate && python -m pytest tests/ --cov=app --cov-report=term-missing 2>&1 | tail -20

run:
	@echo "$(GREEN)Starting AI Service...$(NC)"
	@source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

consumer:
	@echo "$(GREEN)Starting Chat Processor Consumer...$(NC)"
	@source .venv/bin/activate && python app/cli/consumer_entrypoint.py

# Docker convenience commands
docker-qdrant:
	@echo "Starting Qdrant container..."
	@docker run -d \
		--name echoteam-qdrant \
		-p 6333:6333 \
		-p 6334:6334 \
		-v qdrant_data:/qdrant/storage \
		qdrant/qdrant

docker-ollama:
	@echo "Starting Ollama container..."
	@docker run -d \
		--name echoteam-ollama \
		-p 11434:11434 \
		-v ollama_data:/root/.ollama \
		ollama/ollama

docker-all: docker-qdrant docker-ollama
	@echo ""
	@echo "$(GREEN)All containers started!$(NC)"
	@echo "Pull the embedding model:"
	@echo "  docker exec echoteam-ollama ollama pull nomic-embed-text:v1.5"

clean-containers:
	@echo "$(YELLOW)Stopping and removing containers...$(NC)"
	@docker stop $$(docker ps -aq --filter name=echoteam-) 2>/dev/null; \
	docker rm $$(docker ps -aq --filter name=echoteam-) 2>/dev/null
	@echo "$(GREEN)Containers cleaned!$(NC)"

clean-all: clean-containers
	@echo "$(YELLOW)Removing volumes and images...$(NC)"
	@docker volume rm qdrant_data ollama_data 2>/dev/null
	@echo "$(GREEN)All cleaned!$(NC)"

# Show access information
info:
	@echo ""
	@echo "=============================================="
	@echo "         EchoTeam Services                   "
	@echo "=============================================="
	@echo ""
	@echo "Web Interfaces:"
	@echo "  Netdata:     http://localhost:19999"
	@echo "  Langfuse:    http://localhost:3100"
	@echo ""
	@echo "API Endpoints:"
	@echo "  AI Service:  http://localhost:8000"
	@echo "  Docs:        http://localhost:8000/docs"
	@echo ""
	@echo "Infrastructure:"
	@echo "  Qdrant:      http://localhost:6333"
	@echo "  Ollama:      http://localhost:11434"
	@echo ""
	@echo "=============================================="
