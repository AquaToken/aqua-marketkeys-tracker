import asyncio
from decimal import Decimal
from typing import AsyncIterator, List

from django.conf import settings

from asgiref.sync import sync_to_async
from stellar_sdk import AiohttpClient
from stellar_sdk import Asset as StellarAsset
from stellar_sdk import Server

from aqua_marketkeys_tracker.marketkeys.models import Asset, AssetBan


class MarketIsolationLoader:
    CHUNK_SIZE = 50

    HORIZON_URL = settings.HORIZON_URL
    POOL_SIZE = 20

    PATH_TEST_ASSET = StellarAsset.native()
    PATH_TEST_AMOUNT = Decimal(1)

    BAN_REASON = AssetBan.Reason.ISOLATED_MARKET

    async def get_asset_chunks(self) -> AsyncIterator[List[Asset]]:
        index = 0
        while True:
            assets = await sync_to_async(
                lambda: list(Asset.objects.get_chunk(index, self.CHUNK_SIZE)),
            )()

            yield assets

            index = assets[-1].id
            if len(assets) < self.CHUNK_SIZE:
                break

    def process_asset(self, asset: Asset, is_isolated: bool):
        if is_isolated:
            asset.set_ban(self.BAN_REASON)
        else:
            asset.reset_ban(self.BAN_REASON)

    def get_horizon_server(self) -> Server:
        return Server(self.HORIZON_URL, client=AiohttpClient(
            pool_size=self.POOL_SIZE,
        ))

    async def check_asset(self, asset: Asset, server: Server):
        response = await server.strict_send_paths(
            self.PATH_TEST_ASSET,
            str(self.PATH_TEST_AMOUNT),
            [asset.get_stellar_asset()],
        ).call()
        records = response['_embedded']['records']

        await sync_to_async(self.process_asset)(asset, len(records) == 0)

    async def async_run(self):
        async with self.get_horizon_server() as server:
            async for chunk in self.get_asset_chunks():
                await asyncio.gather(*(
                    self.check_asset(asset, server) for asset in chunk
                ))

    def run(self):
        asyncio.run(self.async_run())
