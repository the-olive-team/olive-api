# Olive API

## Setup

### Install [uv][1]

With MacOS and Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

With Windows:

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Sync with `uv`

```bash
uv sync
```

This will install the appropriate Python version, set up the virtualenv, and install both project dependencies and dev dependencies.

This can be run as many times as needed. uv will automatically use the virtualenv[^1].

### Setup migrations to create the tables.

```bash
uv run -m app.backend_pre_start
uv run -m -- alembic upgrade head
uv run -m app.initial_data
```

## How To Run The Server

Run this every time you want to run the server.

```bash
# sets up environment variables
source env

# runs the server
uv run -- fastapi dev app/main.py
```

[^1]: Additional details can be found in the [Discovery of Python environments][2] section.

[1]: https://docs.astral.sh/uv/getting-started/installation/#installation-methods
[2]: https://docs.astral.sh/uv/pip/environments/#using-arbitrary-python-environments
