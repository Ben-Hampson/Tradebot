.PHONY = lint format test


lint:
	poetry run pylint src tests --fail-under=8.4

test:
	poetry run python -m pytest --cov=src tests

format:
	poetry run black run src tests
	poetry run isort run src tests

docker:
	docker-compose -f docker-compose-local-full.yml up --remove-orphans --force-recreate

docker-build:
	docker-compose -f docker-compose-local-full.yml up --build --remove-orphans --force-recreate

docker-ibeam-up:
	docker-compose -f docker-compose-local-ibeam.yml up -d

docker-ibeam-down:
	docker-compose -f docker-compose-local-ibeam.yml down
