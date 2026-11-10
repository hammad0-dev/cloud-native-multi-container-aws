"""Create development secrets without overwriting existing files."""
import os
import secrets
from pathlib import Path
folder = Path(os.getenv('SECRETS_DIR', '.secrets'))
folder.mkdir(mode=0o700, exist_ok=True)
for name in ('db_password', 'flask_secret', 'mysql_root'):
    target = folder / name
    if not target.exists():
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(secrets.token_urlsafe(36))
    os.chmod(target, 0o444)  # Parent directory is 0700; permits nonroot container reads.
print('Development secret files ready; restrict Windows ACLs if applicable.')
