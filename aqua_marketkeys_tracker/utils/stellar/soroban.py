import base64
import binascii
from typing import Optional

from django.conf import settings

from stellar_sdk import Account
from stellar_sdk import Asset as StellarAsset
from stellar_sdk import SorobanServer, StrKey, TransactionBuilder
from stellar_sdk import xdr as stellar_xdr
from stellar_sdk.exceptions import SdkError


# Simulation never submits the transaction, so the fee value is irrelevant.
SIMULATION_BASE_FEE = 10 ** 5


class ContractDecodeError(Exception):
    pass


class TokenResolveError(Exception):
    """Raised when a token contract could not be inspected (RPC or contract error).

    Callers must treat this as retryable: assuming "pure soroban token" on a failed
    lookup would let a Stellar Asset Contract squat a soroban ``Asset`` row.
    """


def decode_data_entry_contract(value: str) -> str:
    """Decode a base64-encoded manageData entry value into a contract id (C...)."""
    try:
        contract_id = base64.b64decode(value).decode('ascii').strip()
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ContractDecodeError(f'Invalid data entry value: {exc}')

    if not StrKey.is_valid_contract(contract_id):
        raise ContractDecodeError(f'Invalid contract id: {contract_id}')

    return contract_id


def get_rpc_server() -> SorobanServer:
    return SorobanServer(settings.SOROBAN_RPC_URL)


def _get_token_name(contract_id: str) -> str:
    """Read ``name()`` from a token contract via simulation.

    Returns an empty string when the contract answers with a non-string value —
    a Stellar Asset Contract always returns a string, so anything else cannot be
    a SAC.
    """
    # The sequence number is not validated during simulation, so there is no need
    # to load the source account from the network.
    source = Account(settings.SOROBAN_SIMULATION_SOURCE, 0)

    transaction = (
        TransactionBuilder(
            source_account=source,
            network_passphrase=settings.STELLAR_PASSPHRASE,
            base_fee=SIMULATION_BASE_FEE,
        )
        .append_invoke_contract_function_op(
            contract_id=contract_id,
            function_name='name',
            parameters=[],
        )
        .set_timeout(30)
        .build()
    )

    try:
        simulated = get_rpc_server().simulate_transaction(transaction)
    except (SdkError, OSError) as exc:
        raise TokenResolveError(f'RPC call failed for {contract_id}: {exc}')

    if simulated.error or not simulated.results:
        raise TokenResolveError(f'name() simulation failed for {contract_id}: {simulated.error}')

    sc_val = stellar_xdr.SCVal.from_xdr(simulated.results[0].xdr)
    if sc_val.type != stellar_xdr.SCValType.SCV_STRING:
        return ''

    return sc_val.str.sc_string.decode('utf-8')


def resolve_classic_asset(contract_id: str) -> Optional[StellarAsset]:
    """Return the classic asset behind a Stellar Asset Contract, or ``None``.

    A SAC address is a one-way hash of ``(code, issuer)``, so the only way to tell
    a SAC from a pure soroban token is to ask the contract for its ``name()``
    (``native`` or ``CODE:ISSUER`` for a SAC) and then verify that the address is
    the SAC of that very asset. The round trip is what makes it unspoofable: a
    hostile token may claim ``name() == 'AQUA:GBNZ…'``, but its own contract id
    will not match ``SAC(AQUA:GBNZ…)``.

    Raises ``TokenResolveError`` when the contract could not be inspected.
    """
    token_name = _get_token_name(contract_id)

    if not token_name:
        return None

    if token_name == 'native':
        asset = StellarAsset.native()
    else:
        name_parts = token_name.split(':')
        if len(name_parts) != 2:
            return None

        code, issuer = name_parts
        if not StrKey.is_valid_ed25519_public_key(issuer):
            return None

        try:
            asset = StellarAsset(code, issuer)
        except (ValueError, TypeError):
            return None

    if asset.contract_id(settings.STELLAR_PASSPHRASE) != contract_id:
        # The name claims a classic asset, but this contract is not its SAC.
        return None

    return asset
