#!/usr/bin/env bash
set -euo pipefail
python -m pytest app/tests -q
terraform -chdir=infrastructure fmt -check
terraform -chdir=infrastructure init -backend=false
terraform -chdir=infrastructure validate
for script in scripts/*.sh; do bash -n "$script"; done
docker compose --env-file .env.example -f compose.yaml -f compose.local.yaml config --quiet
docker compose --env-file .env.example -f compose.yaml -f compose.local.yaml build
