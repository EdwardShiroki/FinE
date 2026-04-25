#!/bin/sh
set -e

COUNT="${1:-1000}"

docker compose exec -T k3s kubectl exec -n fine deploy/fine-backend -- \
  python manage.py seed_demo_data --count "${COUNT}"
