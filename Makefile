.PHONY = lint format pytest


lint:
	poetry run pylint src tests --fail-under=8.4

pytest:
	poetry run python -m pytest --cov=src.crypto2 tests

format:
	poetry run black src tests
	poetry run isort src tests

docker:
	docker-compose -f docker-compose-local-full.yml up --remove-orphans --force-recreate

docker-build:
	docker-compose -f docker-compose-local-full.yml up --build --remove-orphans --force-recreate

docker-ibeam-up:
	docker-compose -f docker-compose-local-ibeam.yml up -d

docker-ibeam-down:
	docker-compose -f docker-compose-local-ibeam.yml down
