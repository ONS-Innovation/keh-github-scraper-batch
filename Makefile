run:
	poetry run python app.py

install:
	poetry install

install-dev:
	poetry install --with dev

clean:
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -rf __pycache__

black:
	poetry run black . || true

ruff:
	poetry run ruff check . || true

pylint:
	poetry run pylint . || true

lint:
	make black
	make ruff
	make pylint
