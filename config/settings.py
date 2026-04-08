"""
Django settings for config project.
"""

import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
PRODUCTION_MODE = config('PRODUCTION_MODE', default=False, cast=bool)

ALLOWED_HOSTS = [
    'psylab-umkt.my.id',
    'www.psylab-umkt.my.id',
    'mail.psylab-umkt.my.id',
    '202.10.44.34',
    '127.0.0.1',
    'localhost',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    
    # Third party
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    
    # Local apps
    'accounts',
    'rooms',
    'tools',
    'practicum',
    'research',
    'core',
    'konseling',     
    "internship",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'config.urls'


# ============================================
# TEMPLATES CONFIGURATION
# ============================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',  # Main templates folder
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.media_url',
                'django.template.context_processors.static', 
                'konseling.context_processors.admin_stats',  
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ============================================
# DATABASE CONFIGURATION — OPTIMIZED
# ============================================
if PRODUCTION_MODE:
    # MySQL untuk Production — OPTIMIZED
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='must1341_psikologilab1_db'),
            'USER': config('DB_USER', default='must1341'),
            'PASSWORD': config('DB_PASSWORD', default='GdV1k38hD3@lE!'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            },
            **({'CONN_MAX_AGE': 300} if PRODUCTION_MODE else {})  # Persistent connection 5 menit
        }
    }
else:
    # SQLite untuk Development — OPTIMIZED
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# REST Framework — OPTIMIZED
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ============================================
# CORS SETTINGS (Based on Production Mode)
# ============================================
if PRODUCTION_MODE:
    CORS_ALLOWED_ORIGINS = [
        "https://psylab-umkt.my.id",
        "https://www.psylab-umkt.my.id",
    ]
else:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

CORS_ALLOW_CREDENTIALS = True

# Internationalization
LANGUAGE_CODE = 'id-id'
TIME_ZONE = 'Asia/Makassar'  # WITA (GMT+8)
USE_I18N = True
USE_TZ = True

# ============================================
# STATIC FILES CONFIGURATION — OPTIMIZED
# ============================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
if (BASE_DIR / 'static').exists():
    STATICFILES_DIRS = [BASE_DIR / 'static']
else:
    STATICFILES_DIRS = []

# Static files compression di production
if PRODUCTION_MODE:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# ============================================
# MEDIA FILES CONFIGURATION
# ============================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================
# EMAIL CONFIGURATION (Based on Production Mode)
# ============================================
_email_override = config('EMAIL_BACKEND_OVERRIDE', default='')

if PRODUCTION_MODE or _email_override == 'smtp':
    EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST          = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT          = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS       = True
    EMAIL_HOST_USER     = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL  = f'Lab Psikologi UMKT <{config("EMAIL_HOST_USER", default="")}>'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'Lab Psikologi UMKT <noreply@localhost>'

# ============================================
# SECURITY SETTINGS (Production Only)
# ============================================
if PRODUCTION_MODE:
    SECURE_SSL_REDIRECT = False
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # TAMBAHKAN INI — wajib untuk Django 4+ di balik reverse proxy
    CSRF_TRUSTED_ORIGINS = [
        'https://psylab-umkt.my.id',
        'https://www.psylab-umkt.my.id',
    ]
    USE_X_FORWARDED_HOST = True

# ============================================
# CACHE & SESSION — OPTIMIZED UNTUK 300 USERS
# ============================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'psylab-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 10000,  # cukup untuk 300 users
            'CULL_FREQUENCY': 3,
        }
    }
}

# Session di cache (10x lebih cepat dari DB)
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 1209600  # 2 minggu
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ============================================
# LOGIN/LOGOUT SETTINGS
# ============================================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# ============================================
# LOGGING CONFIGURATION — OPTIMIZED
# ============================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django_errors.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'ERROR' if PRODUCTION_MODE else 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
# Create logs directory if not exists
(BASE_DIR / 'logs').mkdir(exist_ok=True)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
