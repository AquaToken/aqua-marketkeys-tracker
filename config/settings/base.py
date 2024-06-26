import environ


# Build paths inside the project like this: root(...)
env = environ.Env()

root = environ.Path(__file__) - 3
apps_root = root.path('aqua_marketkeys_tracker')

BASE_DIR = root()


# Base configurations
# --------------------------------------------------------------------------

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Application definition
# --------------------------------------------------------------------------

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
]

THIRD_PARTY_APPS = [
]

LOCAL_APPS = [
    'aqua_marketkeys_tracker.taskapp',
    'aqua_marketkeys_tracker.marketkeys',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# Middleware configurations
# --------------------------------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# Template configurations
# --------------------------------------------------------------------------

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            root('aqua_marketkeys_tracker', 'templates'),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        },
    },
]


# Fixture configurations
# --------------------------------------------------------------------------

FIXTURE_DIRS = [
    root('aqua_marketkeys_tracker', 'fixtures'),
]


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators
# --------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
# --------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

SITE_ID = 1


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
# --------------------------------------------------------------------------

STATIC_URL = '/static/'
STATIC_ROOT = root('static')

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
)

STATICFILES_DIRS = [
    root('aqua_marketkeys_tracker', 'assets'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = root('media')


CELERY_ENABLED = env.bool('CELERY_ENABLED', default=True)
if CELERY_ENABLED:
    # Celery configuration
    # --------------------------------------------------------------------------

    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_TASK_IGNORE_RESULT = True


# Rest framework configuration
# http://www.django-rest-framework.org/api-guide/settings/
# --------------------------------------------------------------------------

REST_FRAMEWORK = {
    'PAGE_SIZE': 30,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}


# Horizon configuration
# --------------------------------------------------------------------------

STELLAR_PASSPHRASE = NotImplemented
HORIZON_URL = NotImplemented


# Market key configuration
# --------------------------------------------------------------------------

MARKET_KEY_THRESHOLD = 10
MARKET_KEY_SIGNER_WEIGHT = 1
UPVOTE_MARKET_KEY_MARKER = NotImplemented
DOWNVOTE_MARKET_KEY_MARKER = NotImplemented

ASSETS_TRACKER_URL = NotImplemented

IGNORE_FLAGS_ASSET_LIST = [
    'USDC:GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN',
    'EURC:GDHU6WRG4IEQXM5NZ4BMPKOXHW76MZM4Y2IEMFDVXBSDP6SJY4ITNPP2',
]
