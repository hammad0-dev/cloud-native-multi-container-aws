import io
import os
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import boto3
from botocore.config import Config
from flask import Flask, abort, redirect, render_template, request, session, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import URL, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

db = SQLAlchemy()
csrf = CSRFProtect()


def secret(name):
    path = os.environ.get(name + '_FILE')
    if not path:
        raise RuntimeError(name + '_FILE is required')
    value = Path(path).read_text().strip()
    if len(value) < 16:
        raise RuntimeError(name + ' must contain at least 16 characters')
    return value


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    object_key = db.Column(db.String(100), unique=True, nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


def create_app(test_config=None):
    app = Flask(__name__)
    if test_config is None:
        uri = URL.create('mysql+pymysql', username=os.getenv('DB_USER', 'vault'),
                         password=secret('DB_PASSWORD'), host=os.environ['DB_HOST'],
                         database=os.getenv('DB_NAME', 'vault'))
        options = {'pool_pre_ping': True, 'pool_recycle': 280,
                   'connect_args': {'connect_timeout': 5, 'read_timeout': 10, 'write_timeout': 10}}
        if os.getenv('DB_TLS', 'true') == 'true':
            options['connect_args'].update(ssl_ca=os.environ['DB_SSL_CA'],
                                           ssl_verify_cert=True, ssl_verify_identity=True)
        app.config.update(SQLALCHEMY_DATABASE_URI=uri, SQLALCHEMY_ENGINE_OPTIONS=options,
                          SECRET_KEY=secret('FLASK_SECRET_KEY'))
    app.config.update(MAX_CONTENT_LENGTH=6 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE', 'true') == 'true',
                      PERMANENT_SESSION_LIFETIME=1800)
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    Migrate(app, db)
    csrf.init_app(app)
    limiter = Limiter(get_remote_address, app=app, storage_uri='memory://', default_limits=[])
    app.extensions['rate_limiter'] = limiter
    app.extensions['s3'] = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'),
        endpoint_url=os.getenv('S3_ENDPOINT_URL'), config=Config(s3={'addressing_style': 'path'}, retries={'max_attempts': 3}))
    app.config['BUCKET'] = os.getenv('S3_BUCKET', 'vault-local')

    def login_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if 'uid' not in session:
                return redirect(url_for('login'))
            return fn(*args, **kwargs)
        return wrapped

    def owned(doc_id):
        return db.session.execute(db.select(Document).filter_by(id=doc_id, owner_id=session['uid'])).scalar_one_or_none() or abort(404)

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(413)
    def too_large(error):
        return 'Upload exceeds request limit.', 413

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return 'Service temporarily unavailable.', 500

    @app.route('/health')
    def health():
        try:
            db.session.execute(text('SELECT 1'))
            return {'status': 'ok'}
        except SQLAlchemyError:
            db.session.rollback()
            return {'status': 'unavailable'}, 503

    @app.route('/register', methods=['GET', 'POST'])
    @limiter.limit('10 per minute')
    def register():
        if request.method == 'POST':
            username = request.form.get('username', '').strip().lower()
            password = request.form.get('password', '')
            if not 3 <= len(username) <= 80 or not 12 <= len(password) <= 128:
                return 'Username: 3-80 characters; password: 12-128 characters.', 400
            db.session.add(User(username=username, password_hash=generate_password_hash(password)))
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return 'Account cannot be created.', 400
            return redirect(url_for('login'))
        return render_template('auth.html', action='Register')

    @app.route('/login', methods=['GET', 'POST'])
    @limiter.limit('5 per minute')
    def login():
        if request.method == 'POST':
            user = db.session.execute(db.select(User).filter_by(username=request.form.get('username', '').strip().lower())).scalar_one_or_none()
            if not user or not check_password_hash(user.password_hash, request.form.get('password', '')[:129]):
                return 'Invalid credentials.', 401
            session.clear()
            session['uid'] = user.id
            session.permanent = True
            return redirect(url_for('index'))
        return render_template('auth.html', action='Login')

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    @login_required
    def index():
        docs = db.session.execute(db.select(Document).filter_by(owner_id=session['uid']).order_by(Document.created_at.desc())).scalars()
        return render_template('index.html', documents=docs)

    @app.post('/upload')
    @login_required
    def upload():
        item = request.files.get('file')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        if not item or not 1 <= len(title) <= 120 or len(description) > 1000:
            return 'Invalid upload fields.', 400
        filename = secure_filename(item.filename or '')[:200]
        data = item.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024:
            abort(413)
        if not data or not filename.lower().endswith('.txt'):
            return 'Only nonempty UTF-8 .txt documents are allowed.', 400
        try:
            decoded = data.decode('utf-8')
            if any(ord(c) < 32 and c not in '\r\n\t' for c in decoded):
                raise ValueError()
        except (UnicodeDecodeError, ValueError):
            return 'Invalid text document.', 400
        key = 'uploads/' + uuid.uuid4().hex
        s3 = app.extensions['s3']
        try:
            s3.put_object(Bucket=app.config['BUCKET'], Key=key, Body=data, ContentType='text/plain', ServerSideEncryption='AES256')
        except Exception:
            return 'Storage temporarily unavailable.', 503
        try:
            db.session.add(Document(owner_id=session['uid'], object_key=key, filename=filename,
                                    title=title, description=description, size=len(data)))
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            try:
                s3.delete_object(Bucket=app.config['BUCKET'], Key=key)
            except Exception:
                app.logger.error('Upload compensation failed; reconcile orphan objects.')
            return 'Metadata unavailable.', 503
        return redirect(url_for('index'))

    @app.get('/documents/<int:doc_id>/download')
    @login_required
    def download(doc_id):
        doc = owned(doc_id)
        try:
            obj = app.extensions['s3'].get_object(Bucket=app.config['BUCKET'], Key=doc.object_key)
            body = obj['Body']
            try:
                data = body.read()
            finally:
                body.close()
            return send_file(io.BytesIO(data), as_attachment=True, download_name=doc.filename, mimetype='text/plain')
        except Exception:
            return 'Storage temporarily unavailable.', 503

    @app.post('/documents/<int:doc_id>/delete')
    @login_required
    def delete(doc_id):
        doc = owned(doc_id)
        try:
            app.extensions['s3'].delete_object(Bucket=app.config['BUCKET'], Key=doc.object_key)
        except Exception:
            return 'Storage temporarily unavailable.', 503
        try:
            db.session.delete(doc)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            return 'Deletion incomplete; retry deletion.', 503
        return redirect(url_for('index'))
    return app
