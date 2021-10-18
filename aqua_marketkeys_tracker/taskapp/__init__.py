import os

from django.conf import settings

from celery import Celery
from celery.schedules import crontab


if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('aqua_marketkeys_tracker')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
app.conf.timezone = 'UTC'


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    from drf_secure_token.tasks import DELETE_OLD_TOKENS

    app.conf.beat_schedule.update({
        'drf_secure_token.tasks.delete_old_tokens': DELETE_OLD_TOKENS,

        'aqua_marketkeys_tracker.marketkeys.tasks.task_update_market_keys': {
            'task': 'aqua_marketkeys_tracker.marketkeys.tasks.task_update_market_keys',
            'schedule': crontab(minute='*/5'),
            'args': (),
        },
    })
