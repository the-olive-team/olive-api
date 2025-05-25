#! /usr/bin/env bash

source venv/bin/activate

source .env && uv run -- fastapi dev app/main.py
