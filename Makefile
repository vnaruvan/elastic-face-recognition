.PHONY: up down logs smoke test clean init

# bring up all services
up: 
	docker compose up --build -d
	@echo "Waiting for LocalStack to be ready..."
	@sleep 5
	@$(MAKE) init

# initialize LocalStack resources (idempotent)
init:
	docker compose exec localstack /bin/bash /etc/localstack/init/ready.d/init.sh || \
	bash scripts/localstack_init.sh

down:
	docker compose down -v

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

logs-worker:
	docker compose logs -f worker

# run smoke test against local API
smoke:
	python scripts/smoke_test.py

# unit tests only (no docker needed)
test:
	pytest tests/ -v

# lint check
lint:
	ruff check .

# format code
fmt:
	ruff format .

clean:
	docker compose down -v --rmi local
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# show LocalStack resources
ls-s3:
	aws --endpoint-url=http://localhost:4566 s3 ls

ls-sqs:
	aws --endpoint-url=http://localhost:4566 sqs list-queues

