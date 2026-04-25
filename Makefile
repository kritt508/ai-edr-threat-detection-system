# AI-EDR Threat Detection System Makefile

.PHONY: install setup run clean docker-up docker-down

# Default action: show help
help:
	@echo "AI-EDR System Management Commands:"
	@echo "  make setup       - Initial setup (venv, deps, .env)"
	@echo "  make run         - Run the Streamlit frontend"
	@echo "  make docker-up   - Start all services using Docker Compose"
	@echo "  make docker-down - Stop all Docker services"
	@echo "  make clean       - Remove temporary files and venv"

setup:
	@chmod +x setup.sh
	@./setup.sh

run:
	@echo "Starting EDR Dashboard..."
	@streamlit run src/frontend/app.py

docker-up:
	@echo "Spinning up Docker containers..."
	@docker-compose -f src/frontend/docker-compose.yml up -d --build

docker-down:
	@echo "Stopping Docker containers..."
	@docker-compose -f src/frontend/docker-compose.yml down

clean:
	@echo "Cleaning up..."
	@rm -rf venv
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Cleanup finished."
