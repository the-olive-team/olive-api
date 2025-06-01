DOCKER := $(shell if which podman >/dev/null 2>/dev/null; then echo podman; else echo docker; fi)
UV_INSTALLED := .installed_uv
VENV := venv
VENV_INSTALLED := $(VENV)/.installed

.PHONY: build
build:
	$(DOCKER) build --platform linux/amd64  -t olive-api .

$(UV_INSTALLED):
	@if [ ! -f $(UV_INSTALLED) ]; then curl -LsSf https://astral.sh/uv/install.sh | sh; fi
	touch $@

$(VENV_INSTALLED): pyproject.toml $(UV_INSTALLED)
	@if [ -d venv ]; then rm -rf venv; fi
	uv venv $(VENV)
	./prestart.sh
	touch $@

.PHONY: venv
$(VENV): $(VENV_INSTALLED)


.PHONY: run_local
run_local: $(VENV)
	./run_local.sh