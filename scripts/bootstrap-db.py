"""One-time operator bootstrap on EC2. Requires explicit cloud authorization.
Run with an operator AWS profile, never grant master-secret access to runtime role.
"""
import json
import os
import secrets
from pathlib import Path
import boto3
import pymysql

def write_secret(name, value):
    path = Path('.secrets') / name
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o400)
    with os.fdopen(fd, 'w') as stream:
        stream.write(value)
    os.chown(path, 10001, 10001)
    os.chmod(path, 0o400)

os.umask(0o077)
Path('.secrets').mkdir(mode=0o700, exist_ok=True)
sm = boto3.Session(profile_name=os.environ['OPERATOR_AWS_PROFILE'], region_name=os.environ['AWS_REGION']).client('secretsmanager')
master = json.loads(sm.get_secret_value(SecretId=os.environ['MASTER_SECRET_ARN'])['SecretString'])
connection = pymysql.connect(host=os.environ['DB_HOST'], user=master['username'], password=master['password'],
    ssl_ca='certs/global-bundle.pem', ssl_verify_cert=True, ssl_verify_identity=True)
# Idempotently use an existing app secret if present, preserving runtime credentials.
try:
    password = sm.get_secret_value(SecretId=os.environ['DATABASE_SECRET_ARN'])['SecretString']
except sm.exceptions.ResourceNotFoundException:
    password = secrets.token_urlsafe(36)
    sm.put_secret_value(SecretId=os.environ['DATABASE_SECRET_ARN'], SecretString=password)
try:
    sm.get_secret_value(SecretId=os.environ['SESSION_SECRET_ARN'])
except sm.exceptions.ResourceNotFoundException:
    sm.put_secret_value(SecretId=os.environ['SESSION_SECRET_ARN'], SecretString=secrets.token_urlsafe(48))
migration_password = secrets.token_urlsafe(36)
try:
    with connection.cursor() as cursor:
        for user, value in [('vault',password), ('vault_migrator',migration_password)]:
            cursor.execute("CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s REQUIRE SSL", (user,value))
            cursor.execute("ALTER USER %s@'%%' IDENTIFIED BY %s REQUIRE SSL", (user,value))
        cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON vault.* TO 'vault'@'%'")
        cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES ON vault.* TO 'vault_migrator'@'%'")
finally:
    connection.close()
write_secret('migration_password', migration_password)
print('Database users provisioned. Migration password stored locally; remove after migrations.')
