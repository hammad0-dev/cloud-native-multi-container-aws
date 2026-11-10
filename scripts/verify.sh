#!/usr/bin/env bash
set -euo pipefail
docker compose ps
curl --fail --silent --show-error http://127.0.0.1:8080/health
# Does not print secret settings, signed URLs or database connection URLs.
docker compose exec -T app python -c 'from application import create_app; a=create_app(); a.extensions["s3"].put_object(Bucket=a.config["BUCKET"],Key="uploads/verification",Body=b"verification"); a.extensions["s3"].get_object(Bucket=a.config["BUCKET"],Key="uploads/verification")["Body"].close(); a.extensions["s3"].delete_object(Bucket=a.config["BUCKET"],Key="uploads/verification"); print("S3 put/get/delete verified")'
