.PHONY: install test lint capture-api verify

install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

capture-api:
	approvaltrace capture-api --root .approvaltrace

verify:
	approvaltrace verify $(RUN_DIR)
