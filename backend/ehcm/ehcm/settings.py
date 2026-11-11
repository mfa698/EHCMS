
import os
from dotenv import load_dotenv
import mailtrap as mt


from pathlib import Path
from datetime import timedelta


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "replace-this-with-a-secure-secret-key"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1"
    ).split(",")
    if host.strip()
]

AT_DELIVERY_REPORT_TOKEN = os.environ.get(
    "AT_DELIVERY_REPORT_TOKEN",
    ""
)

# APPLICATIONS

INSTALLED_APPS = [

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "drf_yasg",
    "rest_framework_simplejwt",
    "rest_framework_swagger",

    "Users",
    "notifications",
    "reports",
    "worklogs",
]






SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': False,
}
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]




# MIDDLEWARE


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]



ROOT_URLCONF = "ehcm.urls"

WSGI_APPLICATION = "ehcm.wsgi.application"


# DATABASE

DATABASES = {

    "default": {

        "ENGINE": "django.db.backends.sqlite3",

        "NAME": BASE_DIR / "db.sqlite3",

    }

}


# CUSTOM USER MODEL

AUTH_USER_MODEL = "Users.User"


AUTHENTICATION_BACKENDS = [

    "django.contrib.auth.backends.ModelBackend",

]


# PASSWORD VALIDATION

AUTH_PASSWORD_VALIDATORS = [

    {
        "NAME":
        "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },

    {
        "NAME":
        "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 10
        }
    },

    {
        "NAME":
        "django.contrib.auth.password_validation.CommonPasswordValidator"
    },

    {
        "NAME":
        "django.contrib.auth.password_validation.NumericPasswordValidator"
    },

]


# DJANGO REST FRAMEWORK

REST_FRAMEWORK = {

    "DEFAULT_AUTHENTICATION_CLASSES": [

        "rest_framework_simplejwt.authentication.JWTAuthentication",

    ],

    "DEFAULT_PERMISSION_CLASSES": [

        "rest_framework.permissions.IsAuthenticated",

    ],

    "DEFAULT_THROTTLE_CLASSES": [

        "rest_framework.throttling.AnonRateThrottle",

    ],

    "DEFAULT_THROTTLE_RATES": {

        "anon": "100/hour",

        "login": "5/minute",

        "otp": "10/minute",

    },

}


# JWT CONFIGURATION

SIMPLE_JWT = {

    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),

    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),

    "ROTATE_REFRESH_TOKENS": True,

    "BLACKLIST_AFTER_ROTATION": True,

    "AUTH_HEADER_TYPES": ("Bearer",),

    "UPDATE_LAST_LOGIN": True,

}


# CACHE
# Local memory is suitable for development only.
# Use Redis for production.

CACHES = {

    "default": {

        "BACKEND":
        "django.core.cache.backends.locmem.LocMemCache",

        "LOCATION": "ehcm-cache",

    }

}







# # ==================================================
# # MAILTRAP EMAIL CONFIGURATION
# # ==================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'isaacevery002@gmail.com'
EMAIL_HOST_PASSWORD = 'agjubisjeluprrby'
EMAIL_PORT = 587


# AFRICA'S TALKING SMS CONFIGURATION

AT_USERNAME = os.environ.get(
    "AT_USERNAME",
    "sandbox"
)

AT_API_KEY = os.environ.get(
    "AT_API_KEY",
    ""
)


# INTERNATIONALIZATION

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Nairobi"

USE_I18N = True

USE_TZ = True


# STATIC FILES

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


# DEFAULT PRIMARY KEY

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# SECURITY SETTINGS

SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_HTTPONLY = True

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"



# Source - https://stackoverflow.com/a/27878592
# Posted by hiteshpariyani, modified by community. See post 'Timeline' for change history
# Retrieved 2026-11-11, License - CC BY-SA 4.0
