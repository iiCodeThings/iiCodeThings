#!/bin/sh
set -e
cd "$(dirname "$0")/../backend"
pwd
. .venv/bin/activate
export PYTHONPATH=.
exec uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
