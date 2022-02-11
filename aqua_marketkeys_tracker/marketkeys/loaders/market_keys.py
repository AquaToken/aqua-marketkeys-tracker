import logging
import sys
from typing import Optional, List

from django.conf import settings
from stellar_sdk import Server

from aqua_marketkeys_tracker.marketkeys.exceptions import MarketKeyParsingError
from aqua_marketkeys_tracker.marketkeys.models import MarketKey
from aqua_marketkeys_tracker.marketkeys.parser import MarketKeyParser
from aqua_marketkeys_tracker.utils.stellar.requests import load_all_records

logger = logging.getLogger(__name__)


class MarketKeyLoader:
    MARKET_KEYS_PAGE_LIMIT = 200
    HORIZON_URL = settings.HORIZON_URL

    def __init__(self, marker_key: str, parser: MarketKeyParser):
        self.parser = parser
        self.marker_key = marker_key

    def parse_market_key(self, account_info: dict) -> Optional[MarketKey]:
        account_id = account_info['account_id']
        if MarketKey.objects.filter(account_id=account_id).exists():
            return

        try:
            return self.parser.parse_account_info(account_info)
        except MarketKeyParsingError:
            logger.warning('Account info skipped.', exc_info=sys.exc_info())

    def activate_market_keys(self, market_keys: List[MarketKey]):
        exists_market_pairs = set()
        for market_key in sorted(market_keys, key=lambda mk: mk.locked_at):
            market_pair = market_key.get_market_pair()
            if market_pair in exists_market_pairs:
                continue

            if not MarketKey.objects.filter_for_market_pair(market_pair).exists():
                market_key.is_active = True

            exists_market_pairs.add(market_pair)

    def load_market_keys(self):
        horizon_server = Server(self.HORIZON_URL)

        request_builder = horizon_server.accounts().for_signer(self.marker_key).order(desc=False)

        new_market_key_list = []
        for account_info in load_all_records(request_builder, page_size=self.MARKET_KEYS_PAGE_LIMIT):
            market_key = self.parse_market_key(account_info)
            if market_key:
                new_market_key_list.append(market_key)

        self.activate_market_keys(new_market_key_list)
        MarketKey.objects.bulk_create(new_market_key_list)
