"""
Account system for the Vowel Space Visualizer (sign-up, login, logout).

Modelled on the KFaligner web app: Flask-Login sessions, users in a local
SQLite database, WTForms with CSRF protection and an arithmetic CAPTCHA on
the login form. Every page and API endpoint requires a logged-in user except
the login/sign-up pages and static files.

State lives in ``instance/`` (not in git):
    instance/users.db     user accounts (password hashes only)
    instance/secret_key   session-signing key, created on first start unless
                          the FLASK_SECRET_KEY environment variable is set
"""
import os
import random
import secrets
from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import (
    flash, jsonify, redirect, render_template, request, session, url_for,
)
from flask_login import (
    LoginManager, UserMixin, current_user, login_user, logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, Regexp, ValidationError,
)

db = SQLAlchemy()

# Endpoints reachable without logging in
PUBLIC_ENDPOINTS = {'login', 'signup', 'static'}


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


def find_user(username):
    """User by name, case-insensitively."""
    return User.query.filter(func.lower(User.username) == username.strip().lower()).first()


class SignupForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Enter a username.'),
        Length(min=3, max=80, message='The username must be 3-80 characters long.'),
        Regexp(r'^[A-Za-z0-9_.-]+$', message='Use letters, digits, "_", "." and "-" only.'),
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Enter your email address.'),
        Email(message='Enter a valid email address.'),
        Length(max=120),
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Enter a password.'),
        Length(min=8, max=128, message='The password must be at least 8 characters long.'),
    ])
    password2 = PasswordField('Confirm password', validators=[
        DataRequired(message='Enter the password again.'),
        EqualTo('password', message='The passwords do not match.'),
    ])
    submit = SubmitField('Sign up')

    def validate_username(self, field):
        if find_user(field.data):
            raise ValidationError('This username is already taken.')

    def validate_email(self, field):
        email = field.data.strip().lower()
        if User.query.filter(func.lower(User.email) == email).first():
            raise ValidationError('This email address is already registered.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(message='Enter your username.')])
    password = PasswordField('Password', validators=[DataRequired(message='Enter your password.')])
    captcha = IntegerField('Security check', validators=[DataRequired(message='Enter the result of the sum.')])
    submit = SubmitField('Log in')


class LogoutForm(FlaskForm):
    """CSRF token only: logout is a POST so other sites cannot trigger it."""


def _load_secret_key(instance_dir):
    """Session key from FLASK_SECRET_KEY, else a persistent random key file."""
    key = os.environ.get('FLASK_SECRET_KEY')
    if key:
        return key
    path = os.path.join(instance_dir, 'secret_key')
    try:
        # O_EXCL: only one gunicorn worker creates the file, the others read it
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, 'w') as f:
            f.write(secrets.token_hex(32))
    for _ in range(50):
        with open(path) as f:
            key = f.read().strip()
        if key:
            return key
        import time
        time.sleep(0.05)   # another worker is still writing the file
    raise RuntimeError(f'Empty secret key file: {path}')


def _safe_next_url(target):
    """Local path to return to after login, or None (never an external URL)."""
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith('/') or target.startswith('//'):
        return None
    return target


def _new_captcha():
    num1, num2 = random.randint(1, 10), random.randint(1, 10)
    session['captcha_answer'] = num1 + num2
    return num1, num2


def init_auth(app):
    """Attach the account system to ``app`` and require login everywhere."""
    instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    os.makedirs(instance_dir, mode=0o700, exist_ok=True)

    app.secret_key = _load_secret_key(instance_dir)
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.config.update(
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(instance_dir, 'users.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Served over HTTPS behind nginx; plain-HTTP cookies only in debug runs
        SESSION_COOKIE_SECURE=not debug,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        WTF_CSRF_TIME_LIMIT=None,
    )

    db.init_app(app)
    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    @app.before_request
    def require_login():
        if request.endpoint in PUBLIC_ENDPOINTS or current_user.is_authenticated:
            return None
        # fetch()/API calls get a JSON 401; page loads go to the login form
        if request.method != 'GET' or request.endpoint in ('example_data',):
            return jsonify({'error': 'Login required. Please log in again.',
                            'login_url': url_for('login')}), 401
        return redirect(url_for('login', next=request.full_path.rstrip('?')))

    @app.context_processor
    def inject_logout_form():
        return {'logout_form': LogoutForm()} if current_user.is_authenticated else {}

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        form = LoginForm()
        if form.validate_on_submit():
            expected = session.pop('captcha_answer', None)
            if expected is None or form.captcha.data != expected:
                flash('The security check answer is not correct.', 'error')
            else:
                user = find_user(form.username.data)
                if user and user.check_password(form.password.data):
                    if not user.is_active:
                        flash('This account has been deactivated. Please contact the administrator.', 'error')
                    else:
                        login_user(user)
                        return redirect(_safe_next_url(request.args.get('next')) or url_for('index'))
                else:
                    flash('Incorrect username or password.', 'error')

        num1, num2 = _new_captcha()
        form.captcha.data = None
        form.captcha.raw_data = None
        return render_template('login.html', form=form, num1=num1, num2=num2)

    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        form = SignupForm()
        if form.validate_on_submit():
            user = User(username=form.username.data.strip(),
                        email=form.email.data.strip().lower())
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created. Please log in.', 'success')
            return redirect(url_for('login'))
        return render_template('signup.html', form=form)

    @app.route('/logout', methods=['POST'])
    def logout():
        if LogoutForm().validate_on_submit():
            logout_user()
            flash('You have been logged out.', 'info')
        return redirect(url_for('login'))
