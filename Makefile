PYTHON ?= python3

.PHONY: install test eval check serve up down demo

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

eval:
	$(PYTHON) -m kalkan eval --out evals/results/latest.json

check: test
	$(PYTHON) -m kalkan eval --check evals/results/latest.json

serve:
	$(PYTHON) -m kalkan serve

demo:
	$(PYTHON) -m kalkan demo --scenario tr-invoice

up:
	docker compose up --build

down:
	docker compose down
