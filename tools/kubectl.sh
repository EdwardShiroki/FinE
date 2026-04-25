#!/bin/sh
set -e

docker compose exec -T k3s kubectl "$@"
