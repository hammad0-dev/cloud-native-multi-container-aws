"""Exercise real HTTP via Nginx using dummy data, without printing credentials."""
import os
import re
import secrets
import requests
base=os.getenv('VAULT_URL','http://127.0.0.1:8080').rstrip('/')

def token(client, path='/'):
    response=client.get(base+path,timeout=10)
    response.raise_for_status()
    return re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)

def account():
    client=requests.Session()
    client.trust_env=False
    name='smoke-'+secrets.token_hex(6)
    password=secrets.token_urlsafe(24)
    for path in ['/register','/login']:
        response=client.post(base+path,data={'username':name,'password':password,
                             'csrf_token':token(client,path)},timeout=10)
        response.raise_for_status()
    assert response.url.rstrip('/') == base
    return client

owner=account()
response=owner.post(base+'/upload',data={'title':'Smoke test','description':'Disposable dummy text',
    'csrf_token':token(owner)},files={'file':('smoke.txt',b'local smoke test','text/plain')},timeout=10)
response.raise_for_status()
identifier=re.search(r'/documents/(\d+)/download',response.text).group(1)
assert owner.get(base+f'/documents/{identifier}/download',timeout=10).content == b'local smoke test'
other=account()
assert other.get(base+f'/documents/{identifier}/download',timeout=10).status_code == 404
assert other.post(base+f'/documents/{identifier}/delete',data={'csrf_token':token(other)},timeout=10).status_code == 404
response=owner.post(base+f'/documents/{identifier}/delete',data={'csrf_token':token(owner)},timeout=10)
response.raise_for_status()
assert owner.get(base+f'/documents/{identifier}/download',timeout=10).status_code == 404
assert owner.get(base+'/health',timeout=10).json()['status'] == 'ok'
print('HTTP smoke passed: register/login, CSRF forms, upload/list/download, owner isolation, delete and health.')
print('Two dummy user accounts remain; the smoke document was deleted.')
