"""Run as root on EC2, using the instance role. Never prints secret values."""
import os
import tempfile
from pathlib import Path
import boto3
os.umask(0o077)
folder = Path('.secrets')
folder.mkdir(mode=0o700, exist_ok=True)
sm = boto3.client('secretsmanager', region_name=os.environ['AWS_REGION'])
for name, variable in [('db_password', 'DATABASE_SECRET_ARN'), ('flask_secret', 'SESSION_SECRET_ARN')]:
    value = sm.get_secret_value(SecretId=os.environ[variable])['SecretString']
    fd, temporary = tempfile.mkstemp(dir=folder)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(value)
        os.chown(temporary, 10001, 10001)
        os.chmod(temporary, 0o400)
        os.replace(temporary, folder / name)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
print('Runtime secret files refreshed; recreate containers to use replacements.')
