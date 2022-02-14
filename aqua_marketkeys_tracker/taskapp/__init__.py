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
    app.conf.beat_schedule.update({
        'aqua_marketkeys_tracker.marketkeys.tasks.task_update_market_keys': {
            'task': 'aqua_marketkeys_tracker.marketkeys.tasks.task_update_market_keys',
            'schedule': crontab(minute='*/5'),
            'args': (),
        },
        'aqua_marketkeys_tracker.marketkeys.tasks.task_update_downvote_market_keys': {
            'task': 'aqua_marketkeys_tracker.marketkeys.tasks.task_update_downvote_market_keys',
            'schedule': crontab(minute='1-59/5'),  # 5n+1
            'args': (),
        },
        'aqua_marketkeys_tracker.marketkeys.tasks.task_update_auth_required': {
            'task': 'aqua_marketkeys_tracker.marketkeys.tasks.task_update_auth_required',
            'schedule': crontab(minute='2-59/5'),  # 5n+2
            'args': (),
        },
        'aqua_marketkeys_tracker.marketkeys.tasks.task_unban_assets': {
            'task': 'aqua_marketkeys_tracker.marketkeys.tasks.task_unban_assets',
            'schedule': crontab(minute='*/5'),
            'args': (),
        },
        'aqua_marketkeys_tracker.marketkeys.tasks.task_check_auth_required': {
            'task': 'aqua_marketkeys_tracker.marketkeys.tasks.task_check_auth_required',
            'schedule': crontab(minute='3-59/5'),  # 5n+3
            'args': (),
        },
    })
