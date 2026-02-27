UV := uv
PYTHON := python
MODULE := src

FUNCTIONS_DEFINITION := data/input/functions_definition.json
INPUT := data/input/function_calling_tests.json
OUTPUT := data/output/function_calls.json

LINT_MYPY_FLAGS := --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

.PHONY: install run debug clean lint lint-strict

install:
	$(UV) sync

run:
	$(UV) run $(PYTHON) -m $(MODULE)

debug:
	$(UV) run $(PYTHON) -m pdb src

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +

lint:
	$(UV) run flake8 .
	$(UV) run mypy . $(LINT_MYPY_FLAGS)

lint-strict:
	$(UV) run flake8 .
	$(UV) run mypy . --strict
