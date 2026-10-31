VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
PYTHON_VERSION := $(shell cat .python-version)

# Passes only if the venv exists, its interpreter runs, and it matches .python-version.
VENV_IS_VALID := test -f $(VENV)/pyvenv.cfg && $(VENV_PYTHON) -c \
	"import platform, sys; sys.exit(not (platform.python_version() + '.').startswith('$(PYTHON_VERSION).'))" \
	>/dev/null 2>&1

.DEFAULT_GOAL := help
.PHONY: help check-uv check-venv venv setup shell lock speckit-check clean reset

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

check-uv: ## Fail if uv is not installed
	@command -v uv >/dev/null 2>&1 || { echo "uv not found: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }

check-venv: ## Fail if the virtualenv is missing, broken, or on the wrong Python
	@if $(VENV_IS_VALID); then \
		echo "$(VENV) is valid: $$($(VENV_PYTHON) --version)"; \
	else \
		echo "$(VENV) is missing, broken, or not on Python $(PYTHON_VERSION). Run: make venv"; \
		exit 1; \
	fi

venv: check-uv ## Create the virtualenv, or recreate it if it is not valid
	@if $(VENV_IS_VALID); then \
		echo "$(VENV) is valid: $$($(VENV_PYTHON) --version)"; \
	else \
		rm -rf $(VENV) && uv venv --python $(PYTHON_VERSION) $(VENV); \
	fi

setup: venv ## Ensure the virtualenv, activate it, and install locked dependencies
	@. $(VENV)/bin/activate && uv sync --locked

shell: venv ## Open a new shell with the virtualenv activated (exit to leave)
	@. $(VENV)/bin/activate && exec $${SHELL:-/bin/sh}

lock: check-uv ## Update uv.lock after changing pyproject.toml
	@uv lock

speckit-check: setup ## Check Spec Kit and its tooling
	@. $(VENV)/bin/activate && specify check

clean: ## Remove Python and tool caches
	@find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \) -not -path './$(VENV)/*' -prune -exec rm -rf {} +

reset: ## Delete the virtualenv and set it up again
	@rm -rf $(VENV)
	@$(MAKE) --no-print-directory setup
