"""
Django settings for demo_portal project - UPDATED WITH TAWK.TO FIX
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("\n" + "="*60)
print("🚀 DEMO PORTAL - CONFIGURATION")
print("="*60)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-fallback')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost').split(',')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'storages',
]

LOCAL_APPS = [
    'accounts',
    'demos',
    'enquiries',
    'notifications',
    'chatbot',
    'core',
    'customers'
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware', 
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'customers.middleware.SmartCSPMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'customers.middleware.EnhancedContentProtectionMiddleware',
    # 'customers.middleware.SecurityViolationRateLimitMiddleware',
   
    # 'customers.middleware.AntiScreenCaptureMiddleware',
    # 'customers.middleware.ScreenshotProtectionMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.RBACMiddleware',
    'accounts.middleware.SystemInfoMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'customers.middleware.CustomerSecurityMiddleware',
    'customers.middleware.ContentProtectionMiddleware',
    'customers.middleware.WebGLFileMiddleware',
    'customers.middleware.CheckUserStatusMiddleware',
    'customers.middleware.BrotliContentEncodingMiddleware',
]


# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# ============================================
# SECURITY SETTINGS
# ============================================
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost').split(',')

CUSTOMER_SECURITY_SETTINGS = {
    'MAX_LOGIN_ATTEMPTS': 5,
    'LOCKOUT_DURATION': 30,  # minutes
    'SESSION_TIMEOUT': 60,   # minutes
    'MAX_VIOLATIONS_PER_DAY': 10,
    'ENABLE_ACTIVITY_LOGGING': True,
    'ENABLE_SECURITY_ALERTS': True,
    'ALLOWED_VIDEO_EXTENSIONS': ['.mp4', '.avi', '.mov'],
    'MAX_FILE_SIZE': 100 * 1024 * 1024,  # 100MB
}

ROOT_URLCONF = 'demo_portal.urls'

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
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'demo_portal.wsgi.application'

# Custom User Model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Database Configuration
DATABASE_ENGINE = os.getenv('DATABASE_ENGINE', 'sqlite3')

if DATABASE_ENGINE == 'sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print("🗄️  DATABASE: SQLite")
elif DATABASE_ENGINE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'demoportal'),
            'USER': os.getenv('POSTGRES_USER', 'demoportal_user'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
            'HOST': os.getenv('POSTGRES_HOST', 'db'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }
    print("🐘 DATABASE: PostgreSQL")

print("="*60 + "\n")

# Password validation
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

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Demo File Upload Settings
DEMO_FILE_SETTINGS = {
    # Video settings
    'VIDEO_MAX_SIZE': 100 * 1024 * 1024,  # 100MB
    'VIDEO_ALLOWED_EXTENSIONS': ['.mp4', '.avi', '.mov', '.wmv'],
    
    # WebGL settings
    'WEBGL_MAX_SIZE': 100 * 1024 * 1024,  # 100MB
    'WEBGL_ALLOWED_EXTENSIONS': ['.html', '.zip', '.gltf', '.glb'],
    
    # Thumbnail settings
    'THUMBNAIL_MAX_SIZE': 5 * 1024 * 1024,  # 5MB
    'THUMBNAIL_ALLOWED_EXTENSIONS': ['.jpg', '.jpeg', '.png', '.webp'],
}

# =====================================
# FILE UPLOAD SETTINGS
# =====================================
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =====================================
# EMAIL CONFIGURATION
# =====================================
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp-mail.outlook.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'support@chrp-india.com')

# =====================================
# CORS SETTINGS
# =====================================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
CORS_ALLOW_CREDENTIALS = True

# =====================================
# SITE CONFIGURATION
# =====================================
SITE_ID = 1
SITE_NAME = 'Demo Portal'
SITE_DESCRIPTION = 'Professional Business Demo Portal - CHRP India'
SITE_URL = 'http://127.0.0.1:8000'

# =====================================
# SECURITY SETTINGS - UPDATED FOR WEBGL
# =====================================
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'  # Changed for WebGL iframe support

# HSTS settings (production only)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Session security
if DEBUG:
    SESSION_COOKIE_SECURE = False  
    CSRF_COOKIE_SECURE = False     
else:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False  

# =====================================
# BLOCKED EMAIL DOMAINS
# =====================================
BLOCKED_EMAIL_DOMAINS = [
    'gmail.com', 'googlemail.com',
    'yahoo.com', 'yahoo.co.in', 'yahoo.co.uk', 'ymail.com', 'rocketmail.com',
    'hotmail.com', 'hotmail.co.uk', 'outlook.com', 'live.com', 'msn.com',
    'aol.com', 'aim.com',
    'icloud.com', 'me.com', 'mac.com',
    'rediffmail.com', 'rediff.com',
    'protonmail.com', 'mail.com', 'gmx.com', 'zoho.com',
    'inbox.com', 'fastmail.com', 'hushmail.com'
]

# =====================================
# DEMO BOOKING CONFIGURATION
# =====================================
DEMO_BOOKING_SETTINGS = {
    'MORNING_START': 9,
    'MORNING_END': 13,
    'AFTERNOON_START': 14,
    'AFTERNOON_END': 19,
    'BLOCKED_DAYS': [6],
    'MAX_REQUESTS_PER_DAY': 3,
    'ADVANCE_BOOKING_DAYS': 30,
}

# =====================================
# CACHE CONFIGURATION
# =====================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'demo-portal-cache',
        'TIMEOUT': 300,
    }
}

# =====================================
# LOGGING CONFIGURATION
# =====================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'demo_portal.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'demo_portal': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Create logs directory
LOGS_DIR = BASE_DIR / 'logs'
if not LOGS_DIR.exists():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

# =====================================
# LOGIN REDIRECT
# =====================================
LOGIN_REDIRECT_URL = '/admin/dashboard/'
LOGIN_URL = '/auth/signin/'
LOGOUT_REDIRECT_URL = '/auth/signin/'

# Session settings
SESSION_COOKIE_AGE = 86400
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False


# =====================================
# STORAGE CONFIGURATION - S3 + LOCAL HYBRID FOR WEBGL
# =====================================

USE_S3 = os.getenv('USE_S3', 'False') == 'True'

if USE_S3:
    # ✅ AWS S3 Settings
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'ap-south-1')
    
    # ✅ Custom domain calculation
    if os.getenv('AWS_S3_CUSTOM_DOMAIN'):
        AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN')
    else:
        AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    
    # S3 Object Parameters
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
        
    AWS_S3_FILE_MIME_TYPES = {
        '.wasm': 'application/wasm',
        '.data': 'application/octet-stream',
        '.unityweb': 'application/octet-stream',
        '.js': 'application/javascript',
        '.json': 'application/json',
        
        # ADD THESE FOR BROTLI:
        '.wasm.br': 'application/wasm',
        '.js.br': 'application/javascript',
        '.data.br': 'application/octet-stream',
        '.framework.js.br': 'application/javascript',
        '.loader.js.br': 'application/javascript',
        '.symbols.json.br': 'application/json',
        
        '.html': 'text/html',
        '.css': 'text/css',
    }

    # IMPORTANT: Update STORAGES configuration
    STORAGES = {
        "default": {
            "BACKEND": "custom_storages.MediaStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    
    # Media URL (S3)
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    
    # ✅ LOCAL PATH for WebGL Extracted Files
    MEDIA_ROOT = BASE_DIR / 'media'
    WEBGL_EXTRACT_ROOT = MEDIA_ROOT / 'webgl_extracted'
    os.makedirs(WEBGL_EXTRACT_ROOT, exist_ok=True)
    
    print("\n" + "="*60)
    print("📦 STORAGE MODE: S3 + LOCAL HYBRID")
    print(f"📍 S3 Bucket: {AWS_STORAGE_BUCKET_NAME}")
    print(f"🌍 Region: {AWS_S3_REGION_NAME}")
    print(f"📁 Local WebGL Extract: {WEBGL_EXTRACT_ROOT}")
    print(f"🔗 Media URL: {MEDIA_URL}")
    print("="*60 + "\n")

else:
    # ✅ Local Storage
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
    WEBGL_EXTRACT_ROOT = MEDIA_ROOT / 'webgl_extracted'
    os.makedirs(WEBGL_EXTRACT_ROOT, exist_ok=True)
    
    print("\n" + "="*60)
    print("📁 STORAGE MODE: LOCAL ONLY")
    print(f"📍 Media Root: {MEDIA_ROOT}")
    print(f"📁 WebGL Extract: {WEBGL_EXTRACT_ROOT}")
    print("="*60 + "\n")

# ✅ WebGL Configuration
WEBGL_SETTINGS = {
    'EXTRACT_ROOT': WEBGL_EXTRACT_ROOT,
    'SERVE_METHOD': 'local',
    'ALLOWED_EXTENSIONS': ['.html', '.zip', '.gltf', '.glb'],
    'MAX_SIZE': 100 * 1024 * 1024,
}

# Backward compatibility
WEBGL_EXTRACT_DIR = WEBGL_EXTRACT_ROOT


# ============================================
# CSP SETTINGS - COMMENTED OUT (Tawk.to fix)
# ============================================
# Content Security Policy Settings
# CSP_DEFAULT_SRC = ("'self'",)
# CSP_SCRIPT_SRC = (
#     "'self'", 
#     "'unsafe-inline'", 
#     "'unsafe-eval'",
#     "https://cdn.jsdelivr.net",
#     "https://cdnjs.cloudflare.com",
#     "https://ajax.googleapis.com",
#     "https://embed.tawk.to",  # ✅ For Tawk chat
# )
# CSP_STYLE_SRC = (
#     "'self'", 
#     "'unsafe-inline'",
#     "https://cdn.jsdelivr.net",
#     "https://cdnjs.cloudflare.com",
# )
# CSP_IMG_SRC = (
#     "'self'", 
#     "data:", 
#     "blob:",
#     "https://*.s3.amazonaws.com",
#     "https://*.s3.*.amazonaws.com",
# )
# CSP_MEDIA_SRC = (
#     "'self'", 
#     "blob:",
#     "https://*.s3.amazonaws.com",  # ✅ All S3 buckets
#     "https://*.s3.*.amazonaws.com",  # ✅ Regional S3
# )
# CSP_CONNECT_SRC = (
#     "'self'",
#     "https://*.s3.amazonaws.com",
#     "https://*.s3.*.amazonaws.com",
#     "https://cdn.jsdelivr.net",
#     "https://embed.tawk.to",
# )
# CSP_FONT_SRC = (
#     "'self'",
#     "https://cdn.jsdelivr.net",
#     "https://cdnjs.cloudflare.com",
# )
# CSP_FRAME_SRC = (
#     "'self'",
#     "https://embed.tawk.to",  # ✅ For Tawk chat widget
# )
