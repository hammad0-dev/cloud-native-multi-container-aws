# Cost and cleanup

This project is not assumed free. Defaults are us-east-1, t3.small EC2, 20 GiB gp3 EBS, one public IPv4, db.t4g.micro Single-AZ MySQL with 20 GiB gp3 and seven-day backups, one S3 bucket and three Secrets Manager secrets (including the RDS-managed master). Instance classes and engines must be available in your selected region.

Recurring categories: EC2 runtime (and possible burst credits), EBS storage/snapshots, public IPv4 allocation, RDS runtime/storage/backup excess/final snapshots, S3 storage and requests, Secrets Manager secrets/API calls, data transfer, and optional CloudWatch/SSM logging. No NAT gateway or load balancer is provisioned. Stopping EC2 does not stop RDS, EBS, IPv4 or retained storage charges. No numerical estimate is claimed: no region-specific quote has been obtained. Before authorization, enter your selected region, hours/month, storage, requests and transfer into the official [AWS Pricing Calculator](https://calculator.aws/) and save the dated estimate. Review [EC2 pricing](https://aws.amazon.com/ec2/pricing/on-demand/), [RDS MySQL pricing](https://aws.amazon.com/rds/mysql/pricing/), [S3 pricing](https://aws.amazon.com/s3/pricing/) and [Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/).

## Explicit destructive workflow (requires authorization)

1. Stop services: `docker compose down` on EC2. Decide which documents and database records to preserve; export them using an authorized operator identity.
2. The bucket has no versioning and force_destroy=false. Review and empty only the project bucket after data-deletion approval. An operator can use `aws s3 rm s3://EXACT_PROJECT_BUCKET --recursive`; this permanently deletes all current objects. Never run this against a guessed bucket.
3. If you independently enabled versioning, delete ALL versions and delete markers through an explicit reviewed inventory, or bucket deletion fails and old bytes remain billable. Do not assume a simple recursive remove clears versions.
4. Choose a unique `final_snapshot_identifier`. Set `deletion_protection=false`, review its plan, and apply that change only after authorization. RDS teardown deliberately requires a final snapshot (skip_final_snapshot=false).
5. `terraform -chdir=infrastructure plan -destroy -out=cleanup.tfplan`; inspect with `terraform -chdir=infrastructure show cleanup.tfplan`. Get explicit destroy authorization before `terraform -chdir=infrastructure apply cleanup.tfplan`.
6. Check the intended region/account for retained RDS snapshots, AWS Backup recovery points, S3 versions/buckets, EBS volumes/snapshots, public addresses, log groups and secrets pending deletion. Final snapshots and backup exports remain billable. Secrets have a recovery window; decide retention deliberately. Delete sensitive local plans and state only after preserving necessary records and confirming cleanup.

Local-only cleanup is `docker compose -f compose.yaml -f compose.local.yaml down --volumes`; it destroys the local MySQL volume. It never belongs in an automatic validation script.
