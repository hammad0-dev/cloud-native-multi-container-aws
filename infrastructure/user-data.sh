#!/bin/bash
set -euo pipefail
dnf update -y
dnf install -y docker python3 python3-pip git
systemctl enable --now docker
# Pinned manual plugin install; update deliberately after reviewing upstream releases.
install -d -m 755 /usr/local/lib/docker/cli-plugins
curl --fail --location --retry 3 https://github.com/docker/compose/releases/download/v5.6.0/docker-compose-linux-x86_64 -o /tmp/docker-compose
curl --fail --location --retry 3 https://github.com/docker/compose/releases/download/v5.6.0/checksums.txt -o /tmp/compose-checksums.txt
(cd /tmp && grep ' docker-compose-linux-x86_64$' compose-checksums.txt | sed 's/docker-compose-linux-x86_64/docker-compose/' | sha256sum -c -)
install -m 755 /tmp/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version
# No runtime secrets, source credentials or passwords in user data.
