# ruff: noqa: F405
from config.settings.base import *  # noqa: F403


DEBUG = True
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

SECRET_KEY = env('SECRET_KEY', default='test_key')

ALLOWED_HOSTS = ['*']
INTERNAL_IPS = ['127.0.0.1']

ADMINS = (
    ('Dev Email', env('DEV_ADMIN_EMAIL', default='admin@localhost')),
)
MANAGERS = ADMINS


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
# --------------------------------------------------------------------------

DATABASES = {
    'default': env.db(default='postgres://localhost/aqua_marketkeys_tracker'),
}


# Email settings
# --------------------------------------------------------------------------

DEFAULT_FROM_EMAIL = 'noreply@example.com'
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

if CELERY_ENABLED:
    MAILING_USE_CELERY = False


# Debug toolbar installation
# --------------------------------------------------------------------------

INSTALLED_APPS += (
    'debug_toolbar',
)

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]
INTERNAL_IPS = ('127.0.0.1',)


if CELERY_ENABLED:
    # Celery configurations
    # http://docs.celeryproject.org/en/latest/configuration.html
    # --------------------------------------------------------------------------

    CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='amqp://guest@localhost//')

    CELERY_TASK_ALWAYS_EAGER = True


# Sentry config
# -------------

SENTRY_ENABLED = False


# Horizon configuration
# --------------------------------------------------------------------------

STELLAR_PASSPHRASE = 'Test SDF Network ; September 2015'
HORIZON_URL = 'https://horizon-testnet.stellar.org'
AQUA_AMM_API_URL = 'https://amm-api-testnet.aqua.network'

SOROBAN_RPC_URL = env('SOROBAN_RPC_URL', default='https://soroban-testnet.stellar.org')
SOROBAN_SIMULATION_SOURCE = env(
    'SOROBAN_SIMULATION_SOURCE',
    default='GAHPYWLK6YRN7CVYZOO4H3VDRZ7PVF5UJGLZCSPAEIKJE2XSWF5LAGER',
)

# Market key configuration
# --------------------------------------------------------------------------

UPVOTE_MARKET_KEY_MARKER = 'GA2UB7VXXXUSEAQUAXXXAQUARIUSVOTINGWALLETXXXPOWEREDBYAQUA'

ASSETS_TRACKER_URL = env('ASSETS_TRACKER_URL', default='https://assets.example.com/')
GOVERNANCE_API_URL = env('GOVERNANCE_API_URL', default='https://governance-api.aqua.network')
ASSET_REGISTRY_ENDPOINT = env('ASSET_REGISTRY_ENDPOINT', default='/api/asset-tokens/')
