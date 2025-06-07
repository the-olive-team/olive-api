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

### Install Minikube

See https://gist.github.com/wholroyd/748e09ca0b78897750791172b2abb051 for wsl.
Note when debugging, `minikube dashboard` can be used tto view pods in cluster.


### Sync with `uv`

```bash
uv sync
```

This will install the appropriate Python version, set up the virtualenv, and install both project dependencies and dev dependencies.

This can be run as many times as needed. uv will automatically use the virtualenv[^1].

### Setup migrations to create the tables.

In this script, three things are run: starting the DB, running alembic migrations, and then seeding the database.

```bash
PYTHONPATH=. uv run bash prestart.sh
```

### Setup pre-commit hooks

This adds ruff as a pre-commit hook.

```bash
uv run -- pre-commit install
```

## How To Run The Server

Run this every time you want to run the server.

```bash
# sets up environment variables
source env

# runs the server
uv run -- fastapi dev app/main.py
```

## Linting and Formatting

For linting and formatting, we are leveraging [Ruff][3]. The config for this is defined inside `pyproject.toml`. It is recommended to set up format on save through something like the [PyCharm Ruff Plugin][4] or [VS Code Ruff Plugin][5]. To run the linter and formatter on the command line, run these:

```bash
# If you have your virtualenv activated and ruff is in your path, you can exclude the
# "uv run -- " prefix.
uv run -- ruff format
uv run -- ruff check --fix
```

[^1]: Additional details can be found in the [Discovery of Python environments][2] section.

[1]: https://docs.astral.sh/uv/getting-started/installation/#installation-methods
[2]: https://docs.astral.sh/uv/pip/environments/#using-arbitrary-python-environments
[3]: https://docs.astral.sh/ruff/
[4]: https://plugins.jetbrains.com/plugin/20574-ruff
[5]: https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff
