import base64
import binascii

from stellar_sdk import StrKey


class ContractDecodeError(Exception):
    pass


def decode_data_entry_contract(value: str) -> str:
    """Decode a base64-encoded manageData entry value into a contract id (C...)."""
    try:
        contract_id = base64.b64decode(value).decode('ascii').strip()
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ContractDecodeError(f'Invalid data entry value: {exc}')

    if not StrKey.is_valid_contract(contract_id):
        raise ContractDecodeError(f'Invalid contract id: {contract_id}')

    return contract_id
