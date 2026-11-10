output "region" { value = var.region }
output "instance_id" { value = aws_instance.app.id }
output "public_ip" { value = aws_instance.app.public_ip }
output "rds_endpoint" { value = aws_db_instance.db.address }
output "bucket_name" { value = aws_s3_bucket.files.id }
output "database_secret_arn" { value = aws_secretsmanager_secret.database.arn }
output "session_secret_arn" { value = aws_secretsmanager_secret.session.arn }
output "master_secret_arn" { value = aws_db_instance.db.master_user_secret[0].secret_arn }
