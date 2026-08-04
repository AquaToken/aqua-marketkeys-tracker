class AssetStringConverter:
    """Matches 'native', classic 'CODE:ISSUER' or a soroban contract id 'C...'.

    Returns the raw string: views resolve it into a contract id via
    `get_contract_id_for_asset_param`.
    """

    code_regex = '[a-zA-Z0-9]{1,12}'
    issuer_regex = 'G[a-zA-Z0-9]{55}'
    contract_regex = 'C[A-Z2-7]{55}'
    regex = f'(native)|({contract_regex})|({code_regex}:{issuer_regex})'

    def to_python(self, value: str) -> str:
        return value

    def to_url(self, value) -> str:
        return str(value)
