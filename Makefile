DOCKER := $(shell if which podman >/dev/null 2>/dev/null; then echo podman; else echo docker; fi)
UV_INSTALLED := .installed_uv
HELM_INSTALLED := .installed_helm
KUBE_INSTALLED := .installed_kubectl
VENV := venv
VENV_INSTALLED := $(VENV)/.installed

.PHONY: build
build:
	$(DOCKER) build --platform linux/amd64  -t olive-api .

$(UV_INSTALLED):
	@if [ ! -f $(UV_INSTALLED) ]; then curl -LsSf https://astral.sh/uv/install.sh | sh; fi
	touch $@

$(HELM_INSTALLED):
	@if [ ! -f $(HELM_INSTALLED) ]; then curl -LsSf https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash; fi
	touch $@

helm: $(HELM_INSTALLED)

$(KUBE_INSTALLED):
	@if [ ! -f $(KUBE_INSTALLED) ]; then curl -LO https://storage.googleapis.com/kubernetes-release/release/v1.16.0/bin/linux/amd64/kubectl; chmod +x ./kubectl; sudo mv ./kubectl /usr/local/bin/kubectl; mkdir -p ~/.kube; fi
	touch $@

kubectl: $(KUBE_INSTALLED)

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