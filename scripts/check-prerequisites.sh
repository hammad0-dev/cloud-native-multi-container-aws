#!/usr/bin/env bash
set -euo pipefail
for command in docker python3 terraform curl; do command -v "$command" >/dev/null || { echo "Missing: $command"; exit 1; }; done
docker compose version
docker info >/dev/null
terraform version
