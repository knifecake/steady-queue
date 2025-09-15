import os
from datetime import timedelta

import environ

from steady_queue.configuration import Configuration

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
    "default": env.db(
        "DB_URL",
        default="postgres://steady_queue:steady_queue@localhost:5432/steady_queue",
    ),
}

if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    DATABASES["default"]["OPTIONS"] = {"pool": {"min_size": 2, "max_size": 4}}


# Tasks
TASKS = {
    "default": {
        "BACKEND": "steady_queue.backend.SteadyQueueBackend",
        "QUEUES": ["default"],
        "OPTIONS": {},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ALLOWED_HOSTS = ["*"]

DEBUG = True

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


STEADY_QUEUE = Configuration.ConfigurationOptions(
    dispatchers=[
        Configuration.DispatcherConfiguration(
            polling_interval=timedelta(seconds=1), batch_size=500
        )
    ],
    workers=[
        Configuration.WorkerConfiguration(
            queues=["*"],
            threads=2,
            polling_interval=timedelta(seconds=0.1),
            processes=2,
        )
    ],
)


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
        "steady_queue": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
