from typing import Iterable, Iterator, List

from django.conf import settings

import requests

from aqua_marketkeys_tracker.marketkeys.models import Asset, AssetBan
from aqua_marketkeys_tracker.utils.stellar.asset import get_asset_string


class AuthFlagsLoader:
    CHUNK_SIZE = 50

    ASSETS_TRACKER_URL = settings.ASSETS_TRACKER_URL.rstrip("/")

    def get_asset_chunks(self) -> Iterator[List[Asset]]:
        index = 0
        while True:
            assets = list(Asset.objects.get_chunk(index, self.CHUNK_SIZE))

            yield assets

            if len(assets) < self.CHUNK_SIZE:
                break

            index = assets[-1].id

    def get_assets_endpoint(self) -> str:
        return f'{self.ASSETS_TRACKER_URL}/api/v1/assets/'

    def load_asset_data(self, assets: Iterable[Asset]) -> List[dict]:
        endpoint = self.get_assets_endpoint()
        params = []
        for asset in assets:
            params.append(
                ('asset', get_asset_string(asset.get_stellar_asset())),
            )

        response = requests.get(endpoint, params=params)
        response.raise_for_status()

        return response.json()['results']

    def process_asset(self, asset: Asset, asset_data: dict):
        if asset_data['auth_required']:
            asset.set_ban(AssetBan.Reason.AUTH_REQUIRED)
        else:
            asset.reset_ban(AssetBan.Reason.AUTH_REQUIRED)
        if asset_data['auth_revocable']:
            asset.set_ban(AssetBan.Reason.AUTH_REVOCABLE)
        else:
            asset.reset_ban(AssetBan.Reason.AUTH_REVOCABLE)
        if asset_data['auth_clawback_enabled']:
            asset.set_ban(AssetBan.Reason.AUTH_CLAWBACK_ENABLED)
        else:
            asset.reset_ban(AssetBan.Reason.AUTH_CLAWBACK_ENABLED)

    def run(self):
        for chunk in self.get_asset_chunks():
            assets_map = {
                get_asset_string(asset.get_stellar_asset()): asset for asset in chunk
            }
            for asset_data in self.load_asset_data(chunk):
                asset = assets_map[asset_data['asset_string']]
                self.process_asset(asset, asset_data)
