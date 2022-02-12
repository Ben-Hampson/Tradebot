.PHONY = lint format


lint:
	poetry run pylint src --fail-under=6.5

format:
	poetry run black src
	poetry run isort src