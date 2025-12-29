import os
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# SECURITY SETTINGS
# ==============================================================================

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

# ALLOWED_HOSTS - Updated for Render deployment
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=lambda v: [s.strip() for s in v.split(',') if s.strip()])

# Add Render domain pattern if not specified
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    # Default hosts for development and basic deployment
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # Pour les filtres de template (timesince, etc.)
]

LOCAL_APPS = [
    'accounts.apps.AccountsConfig',
    'genealogy.apps.GenealogyConfig',
]

THIRD_PARTY_APPS = [
    # Add third-party apps here if needed
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

# ==============================================================================
# MIDDLEWARE - Optimized for production
# ==============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Must be after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',  
    'accounts.middleware.SessionTimeoutMiddleware',          
    'accounts.middleware.SessionSecurityMiddleware',         
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'kanyamukenge_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'kanyamukenge_project.wsgi.application'

# ==============================================================================
# DATABASE - Render PostgreSQL configuration
# ==============================================================================

# Use DATABASE_URL for Render (automatically provided)
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    # Production: Use Render's PostgreSQL database
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Development: Use local PostgreSQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='kanyamukenge_db'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }

# ==============================================================================
# AUTHENTICATION
# ==============================================================================

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Login/Logout URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# ==============================================================================
# SESSION TIMEOUT SETTINGS
# ==============================================================================

# Session timeout in seconds (default: 2 hours)
SESSION_TIMEOUT_SECONDS = config('SESSION_TIMEOUT_SECONDS', default=7200, cast=int)

# Warning time before session expires (default: 5 minutes)
SESSION_WARNING_SECONDS = config('SESSION_WARNING_SECONDS', default=300, cast=int)

# Admin session timeout (can be longer than regular users)
ADMIN_SESSION_TIMEOUT_SECONDS = config('ADMIN_SESSION_TIMEOUT_SECONDS', default=14400, cast=int)  # 4 hours

# Auto-extend session on user activity
SESSION_AUTO_EXTEND = config('SESSION_AUTO_EXTEND', default=False, cast=bool)

# Security features
PREVENT_CONCURRENT_SESSIONS = config('PREVENT_CONCURRENT_SESSIONS', default=False, cast=bool)
CHECK_SESSION_IP = config('CHECK_SESSION_IP', default=False, cast=bool)

# Session security settings
SESSION_COOKIE_AGE = SESSION_TIMEOUT_SECONDS
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Kigali'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# STATIC FILES - Optimized for Render deployment
# ==============================================================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Static file finders
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# ==============================================================================
# WHITENOISE CONFIGURATION - Production optimized
# ==============================================================================

if DEBUG:
    # Development: Simple storage, no compression
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
    WHITENOISE_USE_FINDERS = True
    WHITENOISE_AUTOREFRESH = True
else:
    # Production: Compressed storage for performance
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    WHITENOISE_USE_FINDERS = False
    WHITENOISE_AUTOREFRESH = False

# WhiteNoise settings for production
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0  # 1 year cache for production
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = [
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'zip', 'gz', 'tgz', 'bz2', 'tbz', 'xz', 'br'
]

# ==============================================================================
# MEDIA FILES
# ==============================================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ==============================================================================
# EMAIL CONFIGURATION
# ==============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER

# ==============================================================================
# SECURITY SETTINGS - Enhanced for production
# ==============================================================================

# CSRF Protection - Updated for Render deployment
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS', 
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]
)

# Production security settings
if not DEBUG:
    # Security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    X_FRAME_OPTIONS = 'DENY'
    
    # Cookie security
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    
    # Enable HTTPS redirect if you have SSL configured
    # SECURE_SSL_REDIRECT = True  # Uncomment when you have HTTPS
    # SECURE_HSTS_SECONDS = 31536000
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_HSTS_PRELOAD = True

# ==============================================================================
# LOGGING - Enhanced for production
# ==============================================================================

LOGS_DIR = BASE_DIR / 'logs'
if not LOGS_DIR.exists():
    LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'accounts': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'genealogy': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'session': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Add file logging for production debugging
if not DEBUG and os.access(LOGS_DIR, os.W_OK):
    LOGGING['handlers']['file'] = {
        'level': 'INFO',
        'class': 'logging.FileHandler',
        'filename': LOGS_DIR / 'django.log',
        'formatter': 'verbose',
    }
    
    # Add file handler to loggers
    for logger in ['accounts', 'genealogy', 'session', 'django.security']:
        LOGGING['loggers'][logger]['handlers'].append('file')
    
# ==============================================================================
# MESSAGE FRAMEWORK
# ==============================================================================

from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
    50: 'critical',  # For session security alerts
}

# ==============================================================================
# CACHE SETTINGS - Production optimized
# ==============================================================================

if not DEBUG:
    # Use Redis if available, fallback to database cache
    REDIS_URL = config('REDIS_URL', default=None)
    if REDIS_URL:
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.redis.RedisCache',
                'LOCATION': REDIS_URL,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                },
                'KEY_PREFIX': 'kanyamukenge',
                'TIMEOUT': 300,
            }
        }
    else:
        # Fallback to database cache
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
                'LOCATION': 'cache_table',
            }
        }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

# ==============================================================================
# FILE UPLOAD SETTINGS
# ==============================================================================

# File upload limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB

# ==============================================================================
# ADMIN SETTINGS
# ==============================================================================

ADMIN_URL = config('ADMIN_URL', default='admin/')

# ==============================================================================
# DEVELOPMENT SETTINGS
# ==============================================================================

if DEBUG:
    # Development specific settings
    SESSION_TIMEOUT_SECONDS = config('DEV_SESSION_TIMEOUT_SECONDS', default=1200, cast=int)
    SESSION_WARNING_SECONDS = config('DEV_SESSION_WARNING_SECONDS', default=300, cast=int)
    
    PREVENT_CONCURRENT_SESSIONS = config('DEV_PREVENT_CONCURRENT_SESSIONS', default=False, cast=bool)
    CHECK_SESSION_IP = config('DEV_CHECK_SESSION_IP', default=False, cast=bool)

# ==============================================================================
# CUSTOM SETTINGS FOR KANYAMUKENGE PROJECT
# ==============================================================================

# Project configuration
PROJECT_NAME = "Famille KANYAMUKENGE"
CONTACT_EMAIL = config('CONTACT_EMAIL', default='irengekanyamukenge@gmail.com')
BASE_URL = config('BASE_URL', default='http://127.0.0.1:8000')

# Application settings
INVITATION_EXPIRE_DAYS = 7

DEFAULT_USER_PERMISSIONS = {
    'can_add_children': True,
    'can_modify_own_info': True,
    'can_view_private_info': False,
    'can_export_data': False,
}

PERSON_VISIBILITY_CHOICES = [
    ('public', 'Public'),
    ('family', 'Famille seulement'),
    ('private', 'Privé'),
]

PARENT_CHILD_RELATIONSHIP_TYPES = [
    ('biological', 'Biologique'),
    ('adopted', 'Adopté'),
    ('stepchild', 'Beau-fils/Belle-fille'),
    ('foster', 'Famille Accueil'),
]

PARTNERSHIP_TYPES = [
    ('marriage', 'Mariage'),
    ('partnership', 'Union libre'),
    ('engagement', 'Fiançailles'),
]

GEDCOM_EXPORT_CONFIG = {
    'charset': 'UTF-8',
    'version': '5.5.1',
    'source': 'Famille KANYAMUKENGE - Plateforme Généalogique',
}