import io
import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from moto import mock_aws
from sqlalchemy.exc import SQLAlchemyError
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from application import create_app, db, Document, User, secret

@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_EC2_METADATA_DISABLED', 'true')
    with mock_aws():
        a = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://',
                        'SECRET_KEY': 'testing-only-secret', 'WTF_CSRF_ENABLED': False,
                        'SESSION_COOKIE_SECURE': False, 'RATELIMIT_ENABLED': False})
        a.extensions['s3'].create_bucket(Bucket=a.config['BUCKET'])
        with a.app_context():
            db.create_all()
        yield a

@pytest.fixture
def client(app):
    return app.test_client()

def register(client, name='alice'):
    return client.post('/register', data={'username':name,'password':'test-password-123'})

def login(client, name='alice'):
    return client.post('/login', data={'username':name,'password':'test-password-123'})

def upload(client, data=b'hello world', filename='notes.txt'):
    return client.post('/upload', data={'title':'Notes','description':'Private',
                                      'file':(io.BytesIO(data),filename)})

def test_registration_login(client, app):
    assert register(client).status_code == 302
    assert register(client).status_code == 400
    assert client.post('/login',data={'username':'alice','password':'wrong'}).status_code == 401
    assert login(client).status_code == 302
    with app.app_context():
        assert db.session.get(User,1).password_hash != 'test-password-123'
    assert client.get('/').status_code == 200
    assert client.get('/health').json == {'status':'ok'}

@pytest.mark.parametrize('url,method',[('/', 'get'),('/upload','post'),('/documents/1/download','get'),('/documents/1/delete','post')])
def test_anonymous(client,url,method):
    assert getattr(client,method)(url).status_code == 302

def test_document_lifecycle_and_ownership(client,app):
    register(client);login(client)
    assert upload(client,filename='../../notes.txt').status_code == 302
    with app.app_context():
        doc=db.session.get(Document,1)
        assert doc.filename == 'notes.txt'
        assert doc.object_key.startswith('uploads/') and 'notes' not in doc.object_key
        assert doc.owner_id == 1 and doc.size == 11
    response=client.get('/documents/1/download')
    assert response.data == b'hello world'
    assert 'attachment' in response.headers['Content-Disposition']
    client.post('/logout');register(client,'bob');login(client,'bob')
    assert b'notes.txt' not in client.get('/').data
    assert client.get('/documents/1/download').status_code == 404
    assert client.post('/documents/1/delete').status_code == 404
    client.post('/logout');login(client)
    assert client.post('/documents/1/delete').status_code == 302
    assert client.get('/documents/1/download').status_code == 404
    with app.app_context():
        assert db.session.get(Document,1) is None
    assert app.extensions['s3'].list_objects_v2(Bucket=app.config['BUCKET']).get('KeyCount') == 0

@pytest.mark.parametrize('data,name',[(b'hello','x.html'),(b'\x00bad','x.txt'),(b'\xff','x.txt'),(b'','x.txt')])
def test_reject_files(client,data,name):
    register(client);login(client)
    assert upload(client,data,name).status_code == 400

def test_size(client):
    register(client);login(client)
    assert upload(client,b'a'*(5*1024*1024+1)).status_code == 413
    assert upload(client,b'a'*(7*1024*1024)).status_code == 413

def test_storage_failure(client,app):
    register(client);login(client)
    with patch.object(app.extensions['s3'],'put_object',side_effect=RuntimeError()):
        assert upload(client).status_code == 503
    with app.app_context():
        assert db.session.execute(db.select(Document)).scalars().all() == []

def test_metadata_failure_compensates(client,app):
    register(client);login(client)
    with patch.object(db.session,'commit',side_effect=SQLAlchemyError()):
        assert upload(client).status_code == 503
    assert app.extensions['s3'].list_objects_v2(Bucket=app.config['BUCKET']).get('KeyCount') == 0

def test_delete_failure_retains_metadata(client,app):
    register(client);login(client);upload(client)
    with patch.object(app.extensions['s3'],'delete_object',side_effect=RuntimeError()):
        assert client.post('/documents/1/delete').status_code == 503
    with app.app_context():
        assert db.session.get(Document,1) is not None

def test_secret_file(tmp_path,monkeypatch,capsys):
    path=tmp_path/'secret';path.write_text('a-secure-testing-value\n')
    monkeypatch.setenv('EXAMPLE_FILE',str(path))
    assert secret('EXAMPLE') == 'a-secure-testing-value'
    assert capsys.readouterr().out == ''
    path.write_text('short')
    with pytest.raises(RuntimeError): secret('EXAMPLE')

def test_csrf(app):
    app.config['WTF_CSRF_ENABLED']=True
    c=app.test_client()
    assert c.post('/register',data={'username':'alice','password':'test-password-123'}).status_code == 400
    assert b'csrf_token' in c.get('/register').data


def test_migration_roundtrip(app):
    with app.app_context():
        db.drop_all()
    directory=str(Path(__file__).resolve().parents[1]/'migrations')
    runner=app.test_cli_runner()
    result=runner.invoke(args=['db','upgrade','--directory',directory])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert db.session.execute(db.select(User)).scalars().all() == []
    assert runner.invoke(args=['db','downgrade','--directory',directory]).exit_code == 0
    assert runner.invoke(args=['db','upgrade','--directory',directory]).exit_code == 0


def test_unavailable_database_health(client):
    with patch.object(db.session,'execute',side_effect=SQLAlchemyError()):
        assert client.get('/health').status_code == 503


def test_login_abuse_limit(app):
    limited=create_app(dict(app.config, RATELIMIT_ENABLED=True))
    with limited.app_context():
        db.create_all()
    client=limited.test_client()
    codes=[client.post('/login',data={'username':'unknown','password':'wrong'}).status_code for _ in range(6)]
    assert codes[-1] == 429


def test_production_secret_configuration(tmp_path,monkeypatch,app,capsys):
    for setting in ('DB_PASSWORD','FLASK_SECRET_KEY'):
        path=tmp_path/setting
        path.write_text('test-secret-from-file-12345')
        monkeypatch.setenv(setting+'_FILE',str(path))
    monkeypatch.setenv('DB_HOST','test.example.invalid')
    monkeypatch.setenv('DB_TLS','true')
    monkeypatch.setenv('DB_SSL_CA','/certs/global-bundle.pem')
    production=create_app()
    assert production.secret_key == 'test-secret-from-file-12345'
    assert production.config['SQLALCHEMY_DATABASE_URI'].password == 'test-secret-from-file-12345'
    options=production.config['SQLALCHEMY_ENGINE_OPTIONS']['connect_args']
    assert options['ssl_verify_cert'] is True and options['ssl_verify_identity'] is True
    assert production.config['SESSION_COOKIE_HTTPONLY'] is True
    assert 'test-secret-from-file' not in capsys.readouterr().out
