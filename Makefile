DOCKER := $(shell if which podman >/dev/null 2>/dev/null; then echo podman; else echo docker; fi)


.PHONY: build
build:
	$(DOCKER) build --platform linux/amd64  -t olive-api .