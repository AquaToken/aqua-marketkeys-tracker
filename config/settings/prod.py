# ruff: noqa: F405
import sentry_sdk
from kombu import Exchange, Queue  # NOQA
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from config.settings.base import *  # noqa: F403


environ.Env.read_env()


DEBUG = False

ADMINS = env.json('ADMINS')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

SECRET_KEY = env('SECRET_KEY')


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
# --------------------------------------------------------------------------

DATABASES = {
    'default': env.db(),
}


# Template
# --------------------------------------------------------------------------

TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]


# Email settings
# --------------------------------------------------------------------------

EMAIL_CONFIG = env.email()
vars().update(EMAIL_CONFIG)

SERVER_EMAIL_SIGNATURE = env('SERVER_EMAIL_SIGNATURE', default='aqua_marketkeys_tracker'.capitalize())
DEFAULT_FROM_EMAIL = SERVER_EMAIL = SERVER_EMAIL_SIGNATURE + ' <{0}>'.format(env('SERVER_EMAIL'))


# Celery configurations
# http://docs.celeryproject.org/en/latest/configuration.html
# --------------------------------------------------------------------------

if CELERY_ENABLED:

    CELERY_BROKER_URL = env('CELERY_BROKER_URL')

    CELERY_TASK_DEFAULT_QUEUE = 'aqua_marketkeys_tracker-celery-queue'
    CELERY_TASK_DEFAULT_EXCHANGE = 'aqua_marketkeys_tracker-exchange'
    CELERY_TASK_DEFAULT_ROUTING_KEY = 'celery.aqua_marketkeys_tracker'
    CELERY_TASK_QUEUES = (
        Queue(
            CELERY_TASK_DEFAULT_QUEUE,
            Exchange(CELERY_TASK_DEFAULT_EXCHANGE),
            routing_key=CELERY_TASK_DEFAULT_ROUTING_KEY,
        ),
    )


# Sentry config
# -------------

SENTRY_DSN = env('SENTRY_DSN', default='')
SENTRY_ENABLED = True if SENTRY_DSN else False

if SENTRY_ENABLED:
    sentry_sdk.init(
        SENTRY_DSN,
        traces_sample_rate=0.2,
        integrations=[DjangoIntegration(), CeleryIntegration()],
    )


# Horizon configuration
# --------------------------------------------------------------------------

STELLAR_PASSPHRASE = env('STELLAR_PASSPHRASE', default='Public Global Stellar Network ; September 2015')
HORIZON_URL = env('HORIZON_URL', default='https://horizon.stellar.org')
AQUA_AMM_API_URL = env('AQUA_AMM_API_URL', default='https://amm-api.aqua.network')

SOROBAN_RPC_URL = env('SOROBAN_RPC_URL', default='https://mainnet.sorobanrpc.com')
SOROBAN_SIMULATION_SOURCE = env(
    'SOROBAN_SIMULATION_SOURCE',
    default='GBNZILSTVQZ4R7IKQDGHYGY2QXL5QOFJYQMXPKWRRM5PAV7Y4M67AQUA',
)


# Market key configuration
# --------------------------------------------------------------------------

UPVOTE_MARKET_KEY_MARKER = env('UPVOTE_MARKET_KEY_MARKER')

ASSETS_TRACKER_URL = env('ASSETS_TRACKER_URL')
GOVERNANCE_API_URL = env('GOVERNANCE_API_URL', default='https://governance-api.aqua.network')
ASSET_REGISTRY_ENDPOINT = env('ASSET_REGISTRY_ENDPOINT', default='/api/asset-tokens/')
