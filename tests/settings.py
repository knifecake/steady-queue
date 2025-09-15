import os

import environ

env = environ.Env()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = "fake-key"

INSTALLED_APPS = [
    "django_tasks",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "steady_queue",
    "tests.dummy",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

DATABASES = {
    "default": env.db("DB_URL", default="sqlite:///tests/tmp/db.sqlite3"),
}


# Tasks
TASKS = {
    "default": {
        "BACKEND": "steady_queue.backend.SteadyQueueBackend",
        "QUEUES": ["default"],
        "OPTIONS": {},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

USE_I18N = True
LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
]

TIME_ZONE = "UTC"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
