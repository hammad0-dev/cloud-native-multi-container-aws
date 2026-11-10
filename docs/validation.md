# Validation record ? 2026-11-10

Checks completed on Windows with Python 3.12 and Git Bash; cloud deployment has not been performed.

| Check | Actual result |
|---|---|
| Python dependencies installed | Passed in workspace .venv after authorized network access |
| pytest app/tests -q | **20 passed** (7.15 seconds in final recorded run) |
| Migration upgrade/downgrade/upgrade | Passed against SQLite as part of pytest |
| Secret-file config and TLS flags | Passed with test-only files; no secrets printed |
| Python source compilation | Passed |
| Terraform fmt -check | Passed |
| Terraform init -backend=false | Passed; AWS provider 6.72.0 downloaded; lock file retained |
| Terraform validate | Passed using provider locally; no AWS connectivity implied |
| Bash syntax | Passed for all scripts and EC2 user data using Git Bash |
| Compose local config --quiet | Passed using .env.example |
| IaC security scanner | Checkov/Trivy not installed; no scan result claimed |
| Docker application image build | Passed with Python 3.12.16-slim-bookworm and pinned dependency constraints |
| Local MySQL migrations | Passed against MySQL 8.4.7 |
| Running containers | Nginx, Gunicorn app, MySQL and Moto all healthy |
| Real HTTP smoke through Nginx | Passed: register/login, CSRF forms, upload/list/download, ownership isolation, delete and health |
| AWS identity/plan/apply | Not run; no account/region supplied or resources created |
| Real RDS TLS, IAM and S3 | **Capture after deployment** |
| Regional price quote | Not obtained; no numerical cost estimate claimed |

SQLite/Moto tests verify app behavior, not production MySQL, cloud access policies or AWS connectivity. An initial Docker build exposed a missing constraints-file COPY, which was fixed. Current base images were selected after reviewing official release guidance. Docker Desktop was initially stopped and was started for local verification; registry image downloads experienced TLS timeouts. The end-to-end check also exposed Nginx tmpfs ownership requirements; explicit UID/GID mounts fixed the proxy startup. Sandbox-owned Windows development secrets could not be mounted; an ignored directory created by the normal Windows account resolved it. The final stack passed health checks and the HTTP smoke test. Two dummy users remain locally; their test document was deleted. No AWS deployment success, screenshots or runtime metrics are fabricated.

Re-run checks with `bash scripts/validate.sh` from an activated Python environment. Start the local stack using README commands, then `python scripts/smoke-test.py` to exercise Nginx, Gunicorn, real local MySQL and Moto together. Use the evidence checklist for actual cloud records.

The final run under the normal Windows account used `python -m pytest app/tests -q -p no:cacheprovider --basetemp=validation-private/pytest-handoff` after creating the ignored `validation-private` parent directory. Default pytest temp/cache paths from the sandbox account caused permission errors in an earlier rerun; using a fresh account-owned directory resolved those environment errors.
