PROJECT_NAME=s3dmap

include .env
export $(shell sed 's/=.*//' .env)

.PHONY: build up down restart logs destroy show psql sql

build:
	docker compose -p $(PROJECT_NAME) build

up:
	docker compose -p $(PROJECT_NAME) up -d
	sleep 3
	@echo "Opening Google Chrome..."
	@google-chrome --ignore-certificate-errors --no-sandbox --new-window https://localhost:$(APP_PORT) &

down:
	docker compose -p $(PROJECT_NAME) down

restart:
	docker compose -p $(PROJECT_NAME) down
	docker compose -p $(PROJECT_NAME) up -d

logs:
	docker compose -p $(PROJECT_NAME) logs -f

destroy:
	docker compose -p $(PROJECT_NAME) down --volumes --remove-orphans

full:
	make down && make destroy && make build && make up && make logs

psql:
	@echo "Connecting to PostgreSQL at localhost:$(POSTGRES_PORT_EXPOSE)"
	@PGPASSWORD=$(POSTGRES_PASSWORD) psql -h localhost -p $(POSTGRES_PORT_EXPOSE) -U $(POSTGRES_USER) -d $(POSTGRES_DB)

sql:
	@echo "Executing SQL on PostgreSQL at localhost:$(POSTGRES_PORT_EXPOSE)"
	@PGPASSWORD=$(POSTGRES_PASSWORD) psql -h localhost -p $(POSTGRES_PORT_EXPOSE) -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "${QUERY}"

show:
	@echo "\nShowing containers for $(PROJECT_NAME):"
	@docker ps -a --filter "name=$(PROJECT_NAME)_"
	@echo "\nShowing volumes for $(PROJECT_NAME):"
	@docker volume ls --filter "name=$(PROJECT_NAME)_"

debug_app:
	docker rm -f s3dmap_app
	cd app && PG_HOST=localhost PG_PORT=$(POSTGRES_PORT_EXPOSE) PG_DBNAME=$(POSTGRES_DB) PG_USER=$(POSTGRES_USER) PG_PASSWORD=$(POSTGRES_PASSWORD) python3 ./s3dmap.py

debug_ingestor:
	docker rm -f s3dmap_ingestor
	USER_INPUT_DIR=./user_input_data PG_HOST=localhost PG_PORT=$(POSTGRES_PORT_EXPOSE) PG_DBNAME=$(POSTGRES_DB) PG_USER=$(POSTGRES_USER) PG_PASSWORD=$(POSTGRES_PASSWORD) ./ingestor/ingestor.py

anonymize:
	# usage: make anonymize BUCKET_NAME=bucket-1
	@echo "Anonymizing data in PostgreSQL: $(BUCKET_NAME)..."
	cd ./anonymizer && python3 ./anonymize_bucket.py $(BUCKET_NAME)