import logging
import sys
from typing import List, Optional

from django.conf import settings

from stellar_sdk import Server

from aqua_marketkeys_tracker.marketkeys.exceptions import MarketKeyParsingError
from aqua_marketkeys_tracker.marketkeys.models import MarketKey
from aqua_marketkeys_tracker.marketkeys.parser import parse_account_info
from aqua_marketkeys_tracker.taskapp import app as celery_app
from aqua_marketkeys_tracker.utils.stellar.requests import load_all_records


logger = logging.getLogger()


MARKET_KEYS_PAGE_LIMIT = 200


def _parse_market_key(account_info: dict) -> Optional[MarketKey]:
    account_id = account_info['account_id']
    if MarketKey.objects.filter(account_id=account_id).exists():
        return

    try:
        return parse_account_info(account_info, settings.UPVOTE_MARKET_KEY_MARKER)
    except MarketKeyParsingError:
        logger.warning('Account info skipped.', exc_info=sys.exc_info())


def _activate_market_keys(market_keys: List[MarketKey]):
    exists_market_pairs = set()
    for market_key in sorted(market_keys, key=lambda mk: mk.locked_at):
        market_pair = market_key.get_market_pair()
        if market_pair in exists_market_pairs:
            continue

        if not MarketKey.objects.filter_for_market_pair(market_pair).exists():
            market_key.is_active = True

        exists_market_pairs.add(market_pair)


@celery_app.task(ignore_result=True)
def task_update_market_keys():
    horizon_server = Server(settings.HORIZON_URL)

    request_builder = horizon_server.accounts().for_signer(settings.UPVOTE_MARKET_KEY_MARKER).order(desc=False)

    new_market_key_list = []
    for account_info in load_all_records(request_builder, page_size=MARKET_KEYS_PAGE_LIMIT):
        market_key = _parse_market_key(account_info)
        if market_key:
            new_market_key_list.append(market_key)

    _activate_market_keys(new_market_key_list)
    MarketKey.objects.bulk_create(new_market_key_list)


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
