UV := uv
PYTHON := python
MODULE := src
LINT_TARGETS := src

FUNCTIONS_DEFINITION := data/input/functions_definition.json
INPUT := data/input/function_calling_tests.json
OUTPUT := data/output/function_calls.json

LINT_MYPY_FLAGS := --follow-imports=skip --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

.PHONY: install run debug clean lint lint-strict

install:
	$(UV) sync

run:
	$(UV) run $(PYTHON) -m $(MODULE) --functions_definition $(FUNCTIONS_DEFINITION) --input $(INPUT) --output $(OUTPUT)

debug:
	$(UV) run $(PYTHON) -m pdb src

clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +

lint:
	$(UV) run flake8 $(LINT_TARGETS)
	$(UV) run mypy $(LINT_TARGETS) $(LINT_MYPY_FLAGS)

lint-strict:
	$(UV) run flake8 $(LINT_TARGETS)
	$(UV) run mypy $(LINT_TARGETS) --strict
