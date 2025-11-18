import asyncio
import aiohttp
from decimal import Decimal
from typing import AsyncIterator, List

from django.conf import settings

from asgiref.sync import sync_to_async
from stellar_sdk import AiohttpClient
from stellar_sdk import Asset as StellarAsset
from stellar_sdk import ServerAsync

from aqua_marketkeys_tracker.marketkeys.models import Asset, AssetBan


class MarketIsolationLoader:
    CHUNK_SIZE = 50

    HORIZON_URL = settings.HORIZON_URL
    POOL_SIZE = 20

    STELLAR_PASSPHRASE = settings.STELLAR_PASSPHRASE
    AQUA_AMM_API_URL = settings.AQUA_AMM_API_URL

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

            if len(assets) < self.CHUNK_SIZE:
                break

            index = assets[-1].id

    def process_asset(self, asset: Asset, is_isolated: bool):
        if is_isolated:
            asset.set_ban(self.BAN_REASON)
        else:
            asset.reset_ban(self.BAN_REASON)

    def get_horizon_server(self) -> ServerAsync:
        return ServerAsync(self.HORIZON_URL, client=AiohttpClient(
            pool_size=self.POOL_SIZE,
        ))

    async def check_asset(self, asset: Asset, server: ServerAsync):
        response = await server.strict_send_paths(
            self.PATH_TEST_ASSET,
            str(self.PATH_TEST_AMOUNT),
            [asset.get_stellar_asset()],
        ).call()
        records = response['_embedded']['records']

        is_isolated = len(records) == 0

        # if there's no native path, check soroban path
        if is_isolated:
            async with aiohttp.ClientSession() as session:
                data = {
                    'token_in_address': self.PATH_TEST_ASSET.contract_id(self.STELLAR_PASSPHRASE),
                    'token_out_address': asset.get_stellar_asset().contract_id(self.STELLAR_PASSPHRASE),
                    'amount': int(self.PATH_TEST_AMOUNT * Decimal(1e7)),
                }
                async with session.post(
                    f'{self.AQUA_AMM_API_URL}/api/external/v2/find-path/',
                    json=data
                ) as find_swap_response:
                    if find_swap_response.status == 200:
                        swap_result = await find_swap_response.json()
                        if swap_result.get('success'):
                            is_isolated = False

        await sync_to_async(self.process_asset)(asset, is_isolated)

    async def async_run(self):
        async with self.get_horizon_server() as server:
            async for chunk in self.get_asset_chunks():
                await asyncio.gather(*(
                    self.check_asset(asset, server) for asset in chunk
                ))

    def run(self):
        asyncio.run(self.async_run())
