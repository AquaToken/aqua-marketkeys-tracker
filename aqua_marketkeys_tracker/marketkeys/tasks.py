import logging
import sys
from typing import Optional

from django.conf import settings

from stellar_sdk import Server

from aqua_marketkeys_tracker.marketkeys.exceptions import MarketKeyParsingError
from aqua_marketkeys_tracker.marketkeys.loaders.auth_flags import AuthFlagsLoader
from aqua_marketkeys_tracker.marketkeys.loaders.market_isolation import MarketIsolationLoader
from aqua_marketkeys_tracker.marketkeys.loaders.market_keys import MarketKeyLoader
from aqua_marketkeys_tracker.marketkeys.models import AssetBan, MarketKey
from aqua_marketkeys_tracker.marketkeys.parser import MarketKeyParser, parse_account_info
from aqua_marketkeys_tracker.taskapp import app as celery_app
from aqua_marketkeys_tracker.utils.stellar.requests import load_all_records


logger = logging.getLogger()


MARKET_KEYS_PAGE_LIMIT = 200

ASSETS_ENDPOINT = '/api/v1/assets/'
ASSETS_CHUNK_SIZE = 100


@celery_app.task(ignore_result=True)
def task_update_market_keys():
    marker_key = settings.UPVOTE_MARKET_KEY_MARKER
    parser = MarketKeyParser(marker_key, NotImplemented)
    loader = MarketKeyLoader(marker_key, parser)
    loader.load_market_keys()


def _parse_downvote_market_key(account_info: dict) -> Optional[MarketKey]:
    account_id = account_info['account_id']
    if MarketKey.objects.filter(downvote_account_id=account_id).exists():
        return

    try:
        return parse_account_info(account_info, settings.DOWNVOTE_MARKET_KEY_MARKER)
    except MarketKeyParsingError:
        logger.warning('Account info skipped.', exc_info=sys.exc_info())


@celery_app.task(ignore_result=True)
def task_update_downvote_market_keys():
    horizon_server = Server(settings.HORIZON_URL)

    request_builder = horizon_server.accounts().for_signer(settings.DOWNVOTE_MARKET_KEY_MARKER).order(desc=False)

    for account_info in load_all_records(request_builder, page_size=MARKET_KEYS_PAGE_LIMIT):
        downvote_market_key = _parse_downvote_market_key(account_info)
        if not downvote_market_key:
            continue

        market_key = (
            MarketKey.objects.filter_active().filter_for_market_pair(downvote_market_key.get_market_pair()).first()
        )
        if not market_key or market_key.downvote_account_id:
            continue

        market_key.downvote_account_id = downvote_market_key.account_id
        market_key.save()


@celery_app.task(ignore_result=True)
def task_unban_assets():
    for asset_ban in AssetBan.objects.filter_for_unban():
        asset_ban.unban_asset()


@celery_app.task(ignore_result=True)
def task_check_auth_required():
    AuthFlagsLoader().run()


@celery_app.task(ignore_result=True)
def task_check_market_isolation():
    MarketIsolationLoader().run()
