# Official guidance checked

Consulted during implementation (2026-11-10); recheck before deployment:

- [Docker Compose file-backed secrets](https://docs.docker.com/compose/how-tos/use-secrets/): mounted files and host-file protection.
- [Docker Swarm secrets](https://docs.docker.com/engine/swarm/secrets/): distinct lifecycle and encryption guarantees.
- [Flask web security](https://flask.palletsprojects.com/en/stable/web-security/): request limits, cookies, browser headers and CSRF considerations.
- [RDS MySQL verified TLS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ConnectToInstanceSSL.CLI.html): CA and hostname verification.
- [RDS-managed master passwords](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-secrets-manager.html): Secrets Manager integration.
- [Terraform S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3): native `use_lockfile` locking and state access.
- [AWS Terraform backend guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/terraform-aws-provider-best-practices/backend.html): native S3 locking for Terraform 1.10+.

No numerical AWS price estimate is included without a regional quote. See cost-and-cleanup.md for current official price sources and assumptions.

- [NGINX current releases](https://nginx.org/): stable 1.30.6 selected after checking release/security notices.
- [Official Python image tags](https://hub.docker.com/_/python/tags): Python 3.12.16 Bookworm selected.
- [Compose Linux plugin install](https://docs.docker.com/compose/install/linux/): pinned manual plugin installation and update responsibility.
- [AWS S3 security best practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html): private access and transport controls.
