# ACERO developer workflow. `make verify` is the single acceptance gate.
PY := ./.venv/bin/python
RUFF := ./.venv/bin/ruff
MYPY := ./.venv/bin/mypy

.PHONY: help setup format lint typecheck test policy schemas verify doctor serve pilot clean

help:
	@echo "ACERO make targets:"
	@echo "  setup      create venv (system site packages) and install acero + dev tools"
	@echo "  format     ruff auto-format/fix"
	@echo "  lint       ruff check"
	@echo "  typecheck  mypy"
	@echo "  test       pytest"
	@echo "  policy     validate policy files"
	@echo "  schemas    validate JSON schemas export"
	@echo "  verify     format-check + lint + typecheck + policy + schemas + test"
	@echo "  doctor     environment/policy health check"
	@echo "  pilot      run the Sprint-4 computational pilot"

setup:
	python3 -m venv --system-site-packages .venv
	$(PY) -m pip install -q -e '.[dev]'

format:
	$(RUFF) check --fix src tests
	$(RUFF) format src tests

lint:
	$(RUFF) check src tests

typecheck:
	$(MYPY) src/acero

test:
	$(PY) -m pytest tests

policy:
	$(PY) -m acero.cli.main policy

schemas:
	$(PY) scripts/export_schemas.py --check

verify: lint typecheck policy schemas test
	@echo "VERIFY: all checks passed."

doctor:
	$(PY) -m acero.cli.main doctor

serve:
	$(PY) -m acero.cli.main serve

pilot:
	$(PY) -m acero.cli.main pilot

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache acero_data **/__pycache__
