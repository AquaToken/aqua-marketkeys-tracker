from django.conf import settings

from aqua_marketkeys_tracker.marketkeys.loaders.market_keys import MarketKeyLoader
from aqua_marketkeys_tracker.marketkeys.parser import MarketKeyParser
from aqua_marketkeys_tracker.taskapp import app as celery_app


MARKET_KEYS_PAGE_LIMIT = 200

ASSETS_ENDPOINT = '/api/v1/assets/'
ASSETS_CHUNK_SIZE = 100


@celery_app.task(ignore_result=True)
def task_update_market_keys():
    marker_key = settings.UPVOTE_MARKET_KEY_MARKER
    parser = MarketKeyParser(marker_key, NotImplemented)
    loader = MarketKeyLoader(marker_key, parser)
    loader.load_market_keys()


@celery_app.task(ignore_result=True)
def task_sync_asset_registry():
    from aqua_marketkeys_tracker.marketkeys.loaders.asset_registry import AssetRegistryLoader

    AssetRegistryLoader().run()
