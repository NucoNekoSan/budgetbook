
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env', override=True)

_MISSING = object()


def _require_env(key: str) -> str:
    value = os.environ.get(key, _MISSING)
    if value is _MISSING:
        raise RuntimeError(
            f'環境変数 {key} が設定されていません。'
            f' プロジェクトルートの .env.example を .env にコピーして値を設定してください。'
        )
    return value


def _env_bool(key: str, default: bool = False) -> bool:
    return os.environ.get(key, '').lower() in ('true', '1', 'yes') if os.environ.get(key) else default


SECRET_KEY = _require_env('SECRET_KEY')
DEBUG = _env_bool('DEBUG')
ALLOWED_HOSTS: list[str] = [
    h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()
]

# ---------------------------------------------------------------------------
# HTTPS / 公開モード（ENABLE_HTTPS=1 で有効化）
# ---------------------------------------------------------------------------
_HTTPS = _env_bool('ENABLE_HTTPS')

INSTALLED_APPS = [
    'axes',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_htmx',
    'ledger',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'axes.middleware.AxesMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Security headers（常時有効）
# ---------------------------------------------------------------------------
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

# ---------------------------------------------------------------------------
# Cookie / セッション
# ---------------------------------------------------------------------------
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

SESSION_COOKIE_SECURE = _HTTPS
CSRF_COOKIE_SECURE = _HTTPS

SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE', 86400))

# ---------------------------------------------------------------------------
# HTTPS 専用設定（ENABLE_HTTPS=1 のときだけ有効）
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = _HTTPS
if _HTTPS:
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 31536000))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = _env_bool('ENABLE_HSTS_PRELOAD')

_trusted = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _trusted.split(',') if o.strip()] if _trusted else []

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ---------------------------------------------------------------------------
# Admin URL（env で変更可能）
# ---------------------------------------------------------------------------
ADMIN_URL_PATH = os.environ.get('ADMIN_URL_PATH', 'admin/')

# ---------------------------------------------------------------------------
# django-axes（ログイン試行回数制限）
# ---------------------------------------------------------------------------
AXES_FAILURE_LIMIT = int(os.environ.get('AXES_FAILURE_LIMIT', 5))
AXES_COOLOFF_TIME = float(os.environ.get('AXES_COOLOFF_TIME', 0.5))  # hours
AXES_LOCKOUT_PARAMETERS = ['username']
AXES_RESET_ON_SUCCESS = True
AXES_ENABLED = 'test' not in sys.argv
