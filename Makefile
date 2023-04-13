.PHONY = lint format pytest


lint:
	poetry run pylint src --fail-under=8.4

pytest:
	poetry run python -m pytest --cov=src.crypto2 tests

format:
	poetry run black src tests
	poetry run isort src tests

docker:
	docker-compose up --remove-orphans --force-recreate

docker-build:
	docker-compose up --build --remove-orphans --force-recreate
