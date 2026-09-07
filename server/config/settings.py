import os
from pathlib import Path
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get('APP_ENV') == 'development'
TESTING = os.environ.get('APP_ENV') == 'test'
LOCAL = DEBUG or TESTING
SECRET_KEY = os.environ.get('SECRET_KEY', 'development-only-never-use-in-production' if LOCAL else '')
PUBLIC_URL = os.environ.get('PUBLIC_URL', 'http://localhost:8000' if LOCAL else '').rstrip('/')
origin = urlparse(PUBLIC_URL)
if not LOCAL and (len(SECRET_KEY) < 50 or origin.scheme != 'https' or not origin.hostname):
    raise ImproperlyConfigured('Configure SECRET_KEY (50+ characters) and HTTPS PUBLIC_URL.')
if origin.path not in ('', '/') or origin.username or origin.query or origin.fragment:
    raise ImproperlyConfigured('PUBLIC_URL must be an origin, without path, credentials or query.')
ALLOWED_HOSTS = [origin.hostname] if origin.hostname else []
if LOCAL:
    ALLOWED_HOSTS += ['localhost', '127.0.0.1', 'testserver']
CSRF_TRUSTED_ORIGINS = [PUBLIC_URL] if PUBLIC_URL else []
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
                  'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'portal']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
              'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
              'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
              'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
              'portal.middleware.SecurityHeaders']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'],
              'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request',
              'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
if LOCAL and not os.environ.get('POSTGRES_HOST'):
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'dev.sqlite3'}}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.environ.get('POSTGRES_DB', 'cesaire'),
                 'USER': os.environ.get('POSTGRES_USER', 'cesaire'), 'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
                 'HOST': os.environ.get('POSTGRES_HOST', 'db'), 'PORT': os.environ.get('POSTGRES_PORT', '5432'),
                 'CONN_MAX_AGE': 60, 'CONN_HEALTH_CHECKS': True}}
    if not os.environ.get('POSTGRES_PASSWORD'):
        raise ImproperlyConfigured('POSTGRES_PASSWORD is required.')
AUTH_USER_MODEL = 'portal.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'workspace'
LOGOUT_REDIRECT_URL = 'home'
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = not LOCAL
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 12
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_SSL_REDIRECT = not LOCAL
SECURE_HSTS_SECONDS = 31536000 if not LOCAL else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_PRELOAD = not LOCAL
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
# Enable only with the provided private Caddy -> app network. Never expose app:8000 publicly.
if os.environ.get('TRUST_PROXY') == '1':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
DATA_UPLOAD_MAX_MEMORY_SIZE = 64 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 60
PASSWORD_RESET_TIMEOUT = 3600
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'portal.mail.OutboxBackend'
if TESTING:
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@example.invalid')
if not LOCAL and (not EMAIL_HOST or DEFAULT_FROM_EMAIL.endswith('example.invalid')):
    raise ImproperlyConfigured('Configure SMTP and DEFAULT_FROM_EMAIL before public launch.')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
OPERATOR_NAME = os.environ.get('OPERATOR_NAME', 'Exploitant de test' if LOCAL else '')
PRIVACY_EMAIL = os.environ.get('PRIVACY_EMAIL', 'privacy@example.invalid' if LOCAL else '')
RETENTION_DAYS = int(os.environ.get('RETENTION_DAYS', '365'))
if not LOCAL and (not OPERATOR_NAME or not PRIVACY_EMAIL or PRIVACY_EMAIL.endswith('example.invalid')):
    raise ImproperlyConfigured('Set OPERATOR_NAME and PRIVACY_EMAIL before public launch.')
LOGGING = {'version':1,'disable_existing_loggers':False,'handlers':{'console':{'class':'logging.StreamHandler'}},
           'root':{'handlers':['console'],'level':os.environ.get('LOG_LEVEL','INFO')},
           'loggers':{'django.security':{'handlers':['console'],'level':'WARNING','propagate':False},
                      'django.request':{'handlers':['console'],'level':'CRITICAL' if TESTING else 'WARNING','propagate':False}}}
