#!/bin/sh
set -e

python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput
exec gunicorn fine_project.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 120 --workers 3
