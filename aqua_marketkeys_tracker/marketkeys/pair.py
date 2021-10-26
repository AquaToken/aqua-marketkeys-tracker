from stellar_sdk import Asset

from aqua_marketkeys_tracker.utils.stellar.asset import get_asset_string


class MarketPair:
    asset1: Asset
    asset2: Asset

    def __init__(self, asset1: Asset, asset2: Asset):
        if asset1 == asset2:
            raise ValueError('Assets in pair must be different.')

        self.asset1 = asset1
        self.asset2 = asset2

    def __eq__(self, other):
        return (
            (self.asset1 == other.asset1 and self.asset2 == other.asset2)
            or (self.asset1 == other.asset2 and self.asset2 == other.asset1)
        )

    def __hash__(self):
        asset1_string = get_asset_string(self.asset1)
        asset2_string = get_asset_string(self.asset2)
        return hash('-'.join(sorted([asset1_string, asset2_string])))
