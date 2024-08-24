# olive-api

## Setup
You need to run this only once.
```
# create a virtual environment
python -m venv venv
pip install poetry
```

You may need to run this more than once.
```
# poetry package manager
poetry install
```

## How To Run The Server
Run this every time you want to run the server.
```
# sets up environment variables
source env

# runs the server
fastapi dev app/main.py
```