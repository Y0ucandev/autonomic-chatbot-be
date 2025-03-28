.PHONY: build test

build:
	docker compose up -d --build

lint:
	@echo "Running black and ruff..."
	docker compose -f docker-compose.yml run --rm app black .
	docker compose -f docker-compose.yml run --rm  app ruff check

test: build lint
	@echo "Running tests..."
	docker compose -f docker-compose.yml run --rm app pytest -s -vv
