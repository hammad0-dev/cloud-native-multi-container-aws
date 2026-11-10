# AWS deployment runbook

Nothing in this runbook has been applied by the implementation agent. Commands that create resources, populate secrets, publish images or modify accounts require explicit authorization. Finish local container validation before deployment. Examples use Bash and the default us-east-1; substitute reviewed values.

## 1. Identity and reviewed infrastructure

On your workstation install AWS CLI v2 and Session Manager plugin, Terraform >=1.10 and Docker. Prefer IAM Identity Center temporary credentials:

```bash
aws configure sso --profile vault-operator
aws sso login --profile vault-operator
export AWS_PROFILE=vault-operator AWS_REGION=us-east-1
aws sts get-caller-identity
aws configure get region --profile vault-operator
cp infrastructure/terraform.tfvars.example infrastructure/terraform.tfvars
# Edit region, trusted public IPv4 /32 and selected sizes.
terraform -chdir=infrastructure init
terraform -chdir=infrastructure fmt -check
terraform -chdir=infrastructure validate
terraform -chdir=infrastructure plan -out=review.tfplan
terraform -chdir=infrastructure show review.tfplan
```

The identity/account and region must match your intended account. State and saved plans remain private. This first deployment uses local state so it does not require a nonexistent backend. Optional remote state: separately provision an encrypted, private, versioned S3 bucket with limited operator permissions, then configure an S3 backend with `use_lockfile=true` and `terraform init -migrate-state`. Current native S3 locking is preferred; DynamoDB locking is deprecated. Do not commit backend credentials or state. See [official backend guidance](https://developer.hashicorp.com/terraform/language/backend/s3).

Before asking for apply authorization, provide the actual plan and selected account/region, all resources and sizes, trusted-CIDR port 8080 exposure, secret flow, a dated AWS Calculator estimate, local validation results, unresolved limitations and data-retention choices. Default categories are described in cost-and-cleanup.md; no numeric quote or reviewed cloud plan exists yet.

Only after explicit authorization:

```bash
terraform -chdir=infrastructure apply review.tfplan
terraform -chdir=infrastructure output
aws ssm start-session --target "$(terraform -chdir=infrastructure output -raw instance_id)" --region "$AWS_REGION"
```

Terraform creates a VPC/IGW/routes, one public and two private subnets, app/DB security groups, one t3.small EC2 with encrypted EBS and IMDSv2, Single-AZ encrypted db.t4g.micro RDS MySQL, a private S3 bucket, two empty runtime secret containers plus RDS-managed master secret, and EC2 IAM/SSM policies. Check the real plan; do not assume these defaults remained unchanged.

## 2. Docker and a reproducible release on EC2

User data installs Amazon Linux's Docker package, enables it, and installs the pinned Compose plugin with checksum verification. Inspect `/var/log/cloud-init-output.log` for package-install failures. Amazon Linux packages receive OS updates; record the installed Docker version with release evidence. No secrets are in user data. Work as root in a protected release directory (`sudo -i`). Docker group membership is equivalent to root access.

If bootstrap failed, install the pinned Compose plugin using the [official manual method](https://docs.docker.com/compose/install/linux/). Manual installs require manual updates. Example x86_64 version, recheck support/security before use:

```bash
install -d -m 755 /usr/local/lib/docker/cli-plugins
curl -fL https://github.com/docker/compose/releases/download/v5.6.0/docker-compose-linux-x86_64 -o /tmp/docker-compose
curl -fL https://github.com/docker/compose/releases/download/v5.6.0/checksums.txt -o /tmp/compose-checksums.txt
(cd /tmp && grep ' docker-compose-linux-x86_64$' compose-checksums.txt | sed 's/docker-compose-linux-x86_64/docker-compose/' | sha256sum -c -)
install -m 755 /tmp/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose
systemctl enable --now docker
docker version
docker compose version
install -d -m 700 /opt/document-vault
```

Use a supplied repository URL and recorded full commit (do not publish a repo without authorization):

```bash
git clone YOUR_REVIEWED_REPOSITORY_URL /opt/document-vault/source
cd /opt/document-vault/source
git checkout --detach YOUR_RECORDED_COMMIT_SHA
export RELEASE_SHA=$(git rev-parse HEAD)
export APP_IMAGE=document-vault:$RELEASE_SHA
docker build -f app/Dockerfile -t "$APP_IMAGE" .
docker image inspect "$APP_IMAGE" --format '{{.Id}}'
```

This source-commit path builds locally on EC2 and needs no registry publication. If using an already authorized registry, prefer an immutable digest and `scripts/deploy.sh`; that script deliberately pulls a release image and does not build an untracked working tree. Dependency constraints record resolved package versions. Pin base image digests for stronger reproducibility. Review vulnerability scans before a cloud demo.

## 3. Nonsecret cloud configuration and CA

Create `.env` (ignored), replacing output placeholders. It contains no passwords:

```dotenv
DB_HOST=RDS_ENDPOINT_OUTPUT
DB_TLS=true
AWS_REGION=us-east-1
S3_BUCKET=BUCKET_OUTPUT
APP_IMAGE=document-vault:RECORDED_COMMIT_SHA
HTTP_BIND=0.0.0.0
COOKIE_SECURE=false
```

`COOKIE_SECURE=false` is exclusively for a restricted temporary HTTP demo using dummy data. HTTPS deployment must set it true. Set the shell variables below explicitly too; Compose reads `.env`, Python scripts read the process environment.

```bash
export AWS_REGION=us-east-1
export DB_HOST=RDS_ENDPOINT_OUTPUT
export DATABASE_SECRET_ARN=DATABASE_SECRET_ARN_OUTPUT
export SESSION_SECRET_ARN=SESSION_SECRET_ARN_OUTPUT
export MASTER_SECRET_ARN=MASTER_SECRET_ARN_OUTPUT
mkdir -p certs
curl --fail --location https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o certs/global-bundle.pem
chmod 644 certs/global-bundle.pem
python3 -m venv /opt/document-vault/operator-venv
/opt/document-vault/operator-venv/bin/pip install -r app/requirements.txt
```

Keep the CA bundle current from the [RDS trust store guidance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html); mount it read-only. Do not use an IP instead of the DNS endpoint or turn off verification.

## 4. Separate privileged bootstrap and runtime retrieval

The instance role cannot read master credentials or populate secrets. Configure a temporary **operator** IAM Identity Center profile on this EC2 session, requiring the identity provider/device login your organization supports, and remove its cached access afterwards. Use `aws configure sso --profile vault-bootstrap`, then `aws sso login --profile vault-bootstrap --use-device-code`. This assumes organization-approved operator use on this learning host. If prohibited, use an SSM tunnel and an operator workstation workflow instead; do not broaden the runtime role. The operator needs `GetSecretValue` on the master/app/session ARNs and `PutSecretValue` on app/session ARNs (plus KMS access if using custom keys).

```bash
export OPERATOR_AWS_PROFILE=vault-bootstrap
/opt/document-vault/operator-venv/bin/python scripts/bootstrap-db.py
# Runtime retrieval deliberately uses the instance role, not the operator profile.
unset AWS_PROFILE AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
/opt/document-vault/operator-venv/bin/python scripts/fetch-secrets.py
```

Bootstrap reads the RDS-managed master password without printing it, creates/reuses the app password in Secrets Manager, creates the session secret if missing, creates/updates the `vault` and `vault_migrator` accounts with REQUIRE SSL, and grants DML versus schema privileges separately. An empty secret container is not a usable credential. Existing app secrets are reused. Migration credentials are generated only into a local protected file. Root and the nonroot container UID can access runtime files; they remain sensitive despite encrypted EBS.

Run the versioned migration with a temporary privileged credential mount, never the master account:

```bash
docker compose run --rm --no-deps   -e DB_USER=vault_migrator   -e DB_PASSWORD_FILE=/run/secrets/migration_password   -v "$PWD/.secrets/migration_password:/run/secrets/migration_password:ro"   app flask --app application db upgrade
# Only after migration succeeds:
rm -- .secrets/migration_password
# Log out the operator session; revoke/drop vault_migrator via operator SQL if desired.
aws sso logout
unset OPERATOR_AWS_PROFILE MASTER_SECRET_ARN
docker compose up -d --wait --no-build
```

The startup uses the recorded locally built image. Keep source/compose/config and protected host secrets available for reboots. For later migrations repeat the approved bootstrap privilege path; it rotates the migration account password. Session secret rotation invalidates existing login sessions. After DB secret rotation coordinate ALTER USER, secret refresh and container recreation; changing Secrets Manager alone does not change MySQL users.

## 5. Verify and collect real evidence

```bash
bash scripts/verify.sh
docker compose ps
docker compose logs --tail=100 app nginx
ss -lnt
```

Verify browser registration, upload/list/download/delete, user isolation, health endpoint and TLS database connection. Check the AWS console/CLI for RDS publicly_accessible=false, source-SG-only 3306, private S3 settings and IMDSv2. From a separate authorized client confirm only allowed reverse-proxy access and no reachability on 5000/8000/3306/2375. Check public HTTP access is limited to your CIDR. Capture outputs/screenshots only after running these checks; they remain unverified now. No cloud connectivity is established by Moto tests or Terraform validate.

## 6. HTTPS extension (separate approval)

With a supplied domain, obtain authorization before DNS records or certificate issuance. One supported path is an internet-facing ALB with ACM certificate, HTTP redirect to HTTPS, a target group forwarding to EC2:8080 and an app SG accepting 8080 only from the ALB SG. This adds resources and recurring cost and is not implemented by this Terraform. Alternative: a supported host TLS proxy/ACME setup with persistent certificate storage and renewals, after reviewing 80/443 access and domain ownership. Keep COOKIE_SECURE=true, verify certificate/hostname, and only then use sensitive data. Do not claim HTTPS is deployed until its provisioning and browser checks succeed.
