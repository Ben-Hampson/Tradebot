.PHONY = lint format


lint:
	poetry run pylint src --fail-under=8.4

format:
	poetry run black src
	poetry run isort src