# Operations and troubleshooting

On EC2 use Session Manager; use `sudo` for Docker and root-owned release directories. Use the local overlay in every local command.

```bash
docker compose ps
docker inspect --format '{{json .State.Health}}' document-vault-app-1
docker compose logs --tail=100 app nginx
df -h
free -m
docker stats --no-stream
docker system df
systemctl status docker
curl -f http://127.0.0.1:8080/health
```

| Symptom | Check and recovery |
|---|---|
| MySQL timeout | RDS available, same VPC, DB SG source equals app SG, route tables, correct endpoint; do not open 3306 to the internet. |
| Access denied | Compare DB username and secret ARN metadata; rerun approved bootstrap/rotation, fetch secrets and recreate app. Never echo password. |
| Certificate failure | Refresh official RDS CA bundle, check clock and exact RDS DNS hostname; never disable identity verification. |
| S3 AccessDenied | Verify bucket name, uploads/ prefix, instance profile, role object actions and secure-transport policy. Runtime deliberately lacks ListBucket. |
| Missing role credentials | Check instance profile and IMDSv2 hop limit 2. `aws sts get-caller-identity` shows identity without credentials; do not curl and print the IMDS credential response. |
| Upload 413 | File must be <=5 MiB; multipart request <=6 MiB in Flask and Nginx. Reload/recreate proxy after changes. |
| Database unavailable at startup | Wait for RDS/local MySQL health, run migrations, inspect health; pool pre-ping supports recovery. `docker compose up -d --wait` can be rerun. |
| Disk full | Check Docker log rotation and disk use; remove only reviewed unused images. Avoid `docker system prune --volumes` unless you deliberately intend data loss. |
| Secret PermissionError | Cloud files UID 10001 mode0400, parent root0700; Docker binds individual files. Local parent0700/files0444. Check Windows ACLs. |
| Login loop | Secure cookies require HTTPS; only dummy HTTP demos may set COOKIE_SECURE=false. |
| Nginx cannot resolve app | Ensure app container created and both services share Compose network. Recreate proxy if app container IP changed. |
| Local downloads missing after restart | Moto is ephemeral; create bucket again and delete stale metadata through the UI. Use durable real S3 for cloud. |

After an EC2 reboot Docker starts via systemd and unless-stopped services restart. Secret files must remain available; refresh from Secrets Manager after rotation and use `docker compose up -d --force-recreate`. An explicitly stopped container may need `docker compose up -d`. RDS/S3 data persists independently of container replacement. Replacing EC2 requires redeploying code/config and retrieving secrets, not restoring container writable layers.

`bash scripts/verify.sh` checks DB health and S3 put/get/delete using the runtime role. It writes one non-sensitive verification key and deletes it; run once at a time. Browser testing still verifies end-to-end authentication and authorization. CloudTrail S3 data events are optional and can cost extra; they are not enabled here.

If Windows sandbox-created secret files cannot be mounted by your Docker Desktop account, generate a fresh development-only secret directory as your normal account: set `SECRETS_DIR=./.runtime-secrets` in your shell, run `python scripts/local-secrets.py`, and set the same nonsecret path in `.env`. This directory is ignored by Git and Docker build context. Do not reuse or disclose the inaccessible files. On Linux, prefer the default `.secrets` path and documented owner/mode settings.
