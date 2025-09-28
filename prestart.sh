#! /usr/bin/env bash

source venv/bin/activate

uv sync

source .env

# Let the DB start
PYTHONPATH=. uv run python app/backend_pre_start.py

# Run migrations
PYTHONPATH=. uv run alembic upgrade head

# Create initial data in DB
PYTHONPATH=. uv run python app/initial_data.py
