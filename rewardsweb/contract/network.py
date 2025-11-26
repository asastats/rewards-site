"""Module with functions for retrieving and saving blockchain data."""

import base64
import struct
import time

from algosdk import transaction
from algosdk.account import address_from_private_key
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.encoding import decode_address
from algosdk.error import AlgodHTTPError
from algosdk.logic import get_application_address
from algosdk.transaction import AssetTransferTxn, PaymentTxn
from algosdk.v2client.algod import AlgodClient

from contract.helpers import (
    address_from_box_name,
    app_schemas,
    atc_method_stub,
    box_name_from_address,
    environment_variables,
    private_key_from_mnemonic,
    wait_for_confirmation,
)

ACTIVE_NETWORK = "testnet"
ADD_ALLOCATIONS_BATCH_SIZE = 4


def _add_allocations(network, addresses, amounts):
    """Add or update allocations for a batch of users.

    :param network: network to deploy to (e.g., "testnet")
    :type network: str
    :param addresses: list of user addresses
    :type addresses: list
    :param amounts: list of corresponding allocation amounts
    :type amounts: list
    :var env: environment variables collection
    :type env: dict
    :var client: Algorand Node client instance
    :type client: :class:`AlgodClient`
    :var token_id: Algorand standard asset identifier to be distributed
    :type token_id: int
    :var atc_stub: collection of data required to create atomic transaction
    :type atc_stub: dict
    :var atc: clear program source code
    :type atc: :class:`AtomicTransactionComposer`
    :var microasa_amounts: amounts collection in microASA
    :type microasa_amounts: list
    :var funding_txn: clear program source code
    :type funding_txn: :class:`algosdk.transaction.AssetTransferTxn`
    :var boxes: collection of boxes to create
    :type boxes: list
    :var response: atomic transaction creation response
    :type response: :class:`AtomicTransactionResponse`
    :return: str
    """
    env = environment_variables()

    client = AlgodClient(
        env.get(f"algod_token_{network}"), env.get(f"algod_address_{network}")
    )
    token_id = int(env.get(f"rewards_token_id_{network}"))
    atc_stub = atc_method_stub(client, network)
    atc = AtomicTransactionComposer()

    microasa_amounts = [
        int(amount * 10 ** int(env.get("rewards_token_decimals"))) for amount in amounts
    ]

    funding_txn = AssetTransferTxn(
        sender=atc_stub.get("sender"),
        receiver=get_application_address(atc_stub.get("app_id")),
        amt=sum(microasa_amounts),
        index=token_id,
        sp=client.suggested_params(),
    )
    atc.add_transaction(
        TransactionWithSigner(
            txn=funding_txn,
            signer=atc_stub.get("signer"),
        )
    )

    boxes = [
        (atc_stub.get("app_id"), box_name_from_address(addr)) for addr in addresses
    ]
    atc.add_method_call(
        app_id=atc_stub.get("app_id"),
        method=atc_stub.get("contract").get_method_by_name("add_allocations"),
        sender=atc_stub.get("sender"),
        sp=client.suggested_params(),
        signer=atc_stub.get("signer"),
        method_args=[addresses, microasa_amounts],
        boxes=boxes,
        foreign_assets=[token_id],
    )

    response = atc.execute(client, 2)
    print(f"Allocations added in transaction {response.tx_ids[0]}")
    return response.tx_ids[0]


def _check_balances(client, address, token_id):
    """Return available ALGO and token balances for a given account.

    :param client: Algorand Node client instance
    :type client: :class:`AlgodClient`
    :param address: account's public address
    :type address: str
    :param token_id: Algorand standard asset identifier to be distributed
    :type token_id: int
    :var account_info: account's public information
    :type account_info: dict
    :var available_balance: account's available ALGO balance
    :type available_balance: int
    :var token_balance: account's token balance
    :type token_balance: int
    :return: two-tuple
    """
    account_info = client.account_info(address)
    if not account_info:
        raise ValueError("Can't fetch account info")

    available_balance = account_info.get("amount", 0) - account_info.get(
        "min-balance", 0
    )
    token_balance = next(
        (
            asset.get("amount")
            for asset in account_info.get("assets", [])
            if asset.get("asset-id") == token_id
        ),
        0,
    )

    return available_balance, token_balance


def _reclaim_allocation(network, user_address):
    """Reclaim a user's allocation if it has expired.

    :param network: network to deploy to (e.g., "testnet")
    :type network: str
    :param user_address: The address of the user whose allocation is to be reclaimed
    :type user_address: str
    :var env: environment variables collection
    :type env: dict
    :var client: Algorand Node client instance
    :type client: :class:`AlgodClient`
    :var token_id: Algorand standard asset identifier to be distributed
    :type token_id: int
    :var atc_stub: collection of data required to create atomic transaction
    :type atc_stub: dict
    :var atc: clear program source code
    :type atc: :class:`AtomicTransactionComposer`
    :var response: atomic transaction creation response
    :type response: :class:`AtomicTransactionResponse`
    :return: str
    """
    env = environment_variables()

    client = AlgodClient(
        env.get(f"algod_token_{network}"), env.get(f"algod_address_{network}")
    )
    token_id = int(env.get(f"rewards_token_id_{network}"))
    atc_stub = atc_method_stub(client, network)
    atc = AtomicTransactionComposer()

    atc.add_method_call(
        app_id=atc_stub.get("app_id"),
        method=atc_stub.get("contract").get_method_by_name("reclaim_allocation"),
        sender=atc_stub.get("sender"),
        sp=atc_stub.get("sp"),
        signer=atc_stub.get("signer"),
        method_args=[user_address],
        boxes=[(atc_stub.get("app_id"), box_name_from_address(user_address))],
        foreign_assets=[token_id],
    )
    response = atc.execute(client, 2)
    print(f"Allocations reclaimed in transaction {response.tx_ids[0]}")
    return response.tx_ids[0]


# # PUBLIC
def claimable_amount_for_address(user_address, network=ACTIVE_NETWORK):
    """Check if the provided address can claim their allocation.

    :param user_address: The address of the user to check for claimability
    :type user_address: str
    :param network: network to deploy to (e.g., "testnet")
    :type network: str
    :var env: environment variables collection
    :type env: dict
    :var client: Algorand Node client instance
    :type client: :class:`AlgodClient`
    :var atc_stub: collection of data required to create atomic transaction
    :type atc_stub: dict
    :var app_id: Rewards dApp unique identifier
    :type app_id: int
    :var box_name: user's box name
    :type box_name: bytes
    :var value: user's box value
    :type value: bytes
    :var amount: amount to reclaim
    :type amount: int
    :var expires_at: timestamp when user's claim period ends
    :type expires_at: int
    :return: True if the user can claim, False otherwise
    :rtype: bool
    """
    env = environment_variables()
    client = AlgodClient(
        env.get(f"algod_token_{network}"), env.get(f"algod_address_{network}")
    )
    atc_stub = atc_method_stub(client, network)
    app_id = atc_stub.get("app_id")
    box_name = box_name_from_address(user_address)
    try:
        value = client.application_box_by_name(app_id, box_name).get("value")
        if value is None:
            return False

    except AlgodHTTPError:
        return False

    amount, expires_at = struct.unpack(">QQ", base64.b64decode(value))
    if amount:
        if expires_at < int(time.time()):
            raise ValueError("User's claim period has ended")

        return int(amount / 10 ** int(env.get("rewards_token_decimals")))

    return False


def create_app(client, private_key, approval_program, clear_program, contract_json):
    """Create a new smart contract application on the Algorand blockchain.

    Builds and submits an ApplicationCreate transaction using compiled approval
    and clear programs. Waits for confirmation and returns the resulting app-id
    and genesis hash.

    :param client: Algorand Node client instance.
    :type client: :class:`AlgodClient`
    :param private_key: Creator's private key used to sign the transaction.
    :type private_key: str
    :param approval_program: Compiled TEAL approval program.
    :type approval_program: bytes
    :param clear_program: Compiled TEAL clear program.
    :type clear_program: bytes
    :param contract_json: ARC-56 smart contract specification.
    :type contract_json: dict
    :return: A tuple containing the newly created application ID and genesis hash.
    :rtype: tuple[int, str]
    """
    # define sender as creator
    sender = address_from_private_key(private_key)

    # declare on_complete as NoOp
    on_complete = transaction.OnComplete.NoOpOC.real

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    global_schema, local_schema = app_schemas(contract_json)

    # create unsigned transaction
    txn = transaction.ApplicationCreateTxn(
        sender,
        params,
        on_complete,
        approval_program,
        clear_program,
        global_schema,
        local_schema,
    )

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response["application-index"]
    print("Created new app id: ", app_id)

    return app_id, params.gh


def delete_app(client, private_key, app_id):
    """Delete an existing application on the Algorand blockchain.

    Builds and submits an ApplicationDelete transaction, waits for confirmation,
    and prints application id removed from the blockchain.

    :param client: Algorand Node client instance
    :type client: :class:`AlgodClient`
    :param private_key: application's creator private key used to sign transaction
    :type private_key: str
    :param app_id: application identifier
    :type app_id: int
    """
    # declare sender
    sender = address_from_private_key(private_key)

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    # create unsigned transaction
    txn = transaction.ApplicationDeleteTxn(sender, params, app_id)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    print("Deleted app-id: ", transaction_response["txn"]["txn"]["apid"])


def fund_app(app_id, network, amount=None):
    """Fund the application escrow account with 0.2 Algo.

    Creates an Algod client and sends a payment transaction from the
    creator's account to the application escrow address. Waits for
    confirmation before returning.

    :param app_id: The smart contract application ID.
    :type app_id: int
    :param network: Network where the app is deployed (e.g., ``"testnet"``).
    :type network: str
    :var amount: amount in microAlgos to send to application's escrow
    :type amount: int
    :var env: environment variables collection
    :type env: dict
    :var client: Algorand Node client instance
    :type client: :class:`AlgodClient`
    :var creator_private_key: The private key of the application creator
    :type creator_private_key: str
    :var sender: Derived Algorand wallet address from private key
    :type sender: str
    :var app_address: Application escrow account address
    :type app_address: str
    :var sp: suggested transaction params
    :type sp: :class:`transaction.SuggestedParams`
    :var txn: payment transaction params
    :type txn: :class:`transaction.PaymentTxn`
    :var signed_txn: signed transaction instance
    :type signed_txn: :class:`transaction.SignedTransaction`
    :var tx_id: transaction's unique identifier
    :type tx_id: int
    """
    env = environment_variables()

    if amount is None:
        amount = env.get("dapp_minimum_algo", 100_000)

    client = AlgodClient(
        env.get(f"algod_token_{network}"), env.get(f"algod_address_{network}")
    )
    creator_private_key = private_key_from_mnemonic(
        env.get(f"admin_{network}_mnemonic")
    )
    sender = address_from_private_key(creator_private_key)
    app_address = get_application_address(app_id)
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 1000

    txn = PaymentTxn(
        sender=sender,
        sp=sp,
        receiver=app_address,
        amt=amount,
    )

    signed_txn = txn.sign(creator_private_key)
    tx_id = signed_txn.transaction.get_txid()
    client.send_transactions([signed_txn])
    wait_for_confirmation(client, tx_id)
    print(f"Funded app {app_id} with {amount / 1_000_000} Algo in transaction {tx_id}")


def process_allocations(network, addresses, amounts):
    """Process allocations after performing a couple of checks.

    :param network: network to deploy to (e.g., "testnet")
    :type network: str
    :param addresses: list of user addresses
    :type addresses: list
    :param amounts: list of corresponding allocation amounts
    :type amounts: list
    :var env: environment variables collection
    :type env: dict
    :var client: Algorand Node client instance
    :type client: :class:`AlgodClient`
    :var token_id: Algorand standard asset identifier to be distributed
    :type token_id: int
    :var atc_stub: collection of data required to create atomic transaction
    :type atc_stub: dict
    :var admin_address: Rewards Suite smart contract admin address
    :type admin_address: str
    :var app_address: Rewards Suite smart contract address
    :type app_address: str
    :var app_id: Rewards dApp unique identifier
    :type app_id: int
    :var dapp_minimum_algo: minimum required ALGO for dApp
    :type dapp_minimum_algo: int
    :var app_algo_balance: dApp's ALGO balance
    :type app_algo_balance: int
    :var admin_algo_balance: admin's ALGO balance
    :type admin_algo_balance: int
    :var admin_token_balance: admin's token balance
    :type admin_token_balance: int
    """
    env = environment_variables()
    client = AlgodClient(
        env.get(f"algod_token_{network}"), env.get(f"algod_address_{network}")
    )
    token_id = int(env.get(f"rewards_token_id_{network}"))
    atc_stub = atc_method_stub(client, network)
    admin_address = atc_stub.get("sender")
    app_id = atc_stub.get("app_id")
    app_address = get_application_address(app_id)
    dapp_minimum_algo = int(env.get("dapp_minimum_algo") or 100_000)

    app_algo_balance, _ = _check_balances(client, app_address, token_id)
    if app_algo_balance < dapp_minimum_algo:
        admin_algo_balance, _ = _check_balances(client, admin_address, token_id)
        if admin_algo_balance < dapp_minimum_algo:
            raise ValueError("Not enough ALGO in admin account to fund the app")

        fund_app(app_id, network)

    _, admin_token_balance = _check_balances(client, admin_address, token_id)
    if admin_token_balance < sum(
        int(amount * 10 ** int(env.get("rewards_token_decimals"))) for amount in amounts
    ):
        raise ValueError("Not enough token in admin account to process allocations")

    return _add_allocations(network, addresses, amounts)


def process_allocations_for_contributions(contributions, allocations_callback):
    """Process allocations for applicable contributors from `contributions`.

    :param contributions: collection of contributions connected to closed issue
    :type contributions: :class:`core.models.Contribution`
    :param allocations_callback: callback function to retrieve addresses and amounts
    :type allocations_callback: object
    :var addresses: list of contributor addresses
    :type addresses: list
    :var amounts: list of corresponding allocation amounts
    :type amounts: list
    :var batch_addresses: curent batch of contributor addresses
    :type batch_addresses: list
    :var batch_amounts: curent batch of corresponding allocation amounts
    :type batch_amounts: list
    :yield: two-tuple
    """
    addresses, amounts = allocations_callback(contributions)
    if not addresses:
        yield False, []
        return

    for i in range(0, len(addresses), ADD_ALLOCATIONS_BATCH_SIZE):
        batch_addresses = addresses[i : i + ADD_ALLOCATIONS_BATCH_SIZE]
        batch_amounts = amounts[i : i + ADD_ALLOCATIONS_BATCH_SIZE]

        try:
            result = process_allocations(ACTIVE_NETWORK, batch_addresses, batch_amounts)
            yield result, batch_addresses

        except ValueError:
            yield False, []


def process_reclaim_allocation(user_address, network=ACTIVE_NETWORK):
    """Process reclaim allocation after performing a couple of checks.

    :param user_address: The address of the user whose allocation is to be reclaimed
    :type user_address: str
    :param network: network to deploy to (e.g., "testnet")
    :type network: str
    :var env: environment variables collection
    :type env: dict
    :var client: Algorand Node client instance
    :type client: :class:`AlgodClient`
    :var atc_stub: collection of data required to create atomic transaction
    :type atc_stub: dict
    :var app_id: Rewards dApp unique identifier
    :type app_id: int
    :var box_name: user's box name
    :type box_name: bytes
    :var value: user's box value
    :type value: bytes
    :var amount: amount to reclaim
    :type amount: int
    :var expires_at: timestamp when user's claim period ends
    :type expires_at: int
    """
    env = environment_variables()
    client = AlgodClient(
        env.get(f"algod_token_{network}"), env.get(f"algod_address_{network}")
    )
    atc_stub = atc_method_stub(client, network)
    app_id = atc_stub.get("app_id")
    box_name = box_name_from_address(user_address)
    value = client.application_box_by_name(app_id, box_name).get("value")
    if value is None:
        raise ValueError("No user's box")

    amount, expires_at = struct.unpack(">QQ", base64.b64decode(value))
    if expires_at > int(time.time()):
        raise ValueError("User claim period hasn't ended")

    if amount > 0:
        return _reclaim_allocation(network, user_address)


def reclaimable_addresses(network="testnet"):
    """Return collection of addresses that can be reclaimed.

    :param network: network to deploy to (e.g., "testnet")
    :type network: str
    :var env: environment variables collection
    :type env: dict
    :var client: Algorand Node client instance
    :type client: :class:`AlgodClient`
    :var atc_stub: collection of data required to create atomic transaction
    :type atc_stub: dict
    :var app_id: Rewards dApp unique identifier
    :type app_id: int
    :var reclaimable_addresses: collection of addresses that can be reclaimed
    :type reclaimable_addresses: list
    :var boxes: collection of user's boxes
    :type boxes: list
    :var box: user's box
    :type box: dict
    :var box_name: user's box name
    :type box_name: bytes
    :var user_address: user's public address
    :type user_address: str
    :var value: user's box value
    :type value: bytes
    :var amount: amount to reclaim
    :type amount: int
    :var expires_at: timestamp when user's claim period ends
    :type expires_at: int
    :return: collection of addresses that can be reclaimed
    :rtype: list
    """
    env = environment_variables()
    client = AlgodClient(
        env.get(f"algod_token_{network}"), env.get(f"algod_address_{network}")
    )
    atc_stub = atc_method_stub(client, network)
    app_id = atc_stub.get("app_id")
    reclaimable_addresses = []
    boxes = client.application_boxes(app_id).get("boxes", [])
    for box in boxes:
        user_address = address_from_box_name(box.get("name"))
        box_name = base64.b64decode(box.get("name"))
        value = client.application_box_by_name(app_id, box_name).get("value")
        if value:
            amount, expires_at = struct.unpack(">QQ", base64.b64decode(value))
            if expires_at < int(time.time()) and amount > 0:
                reclaimable_addresses.append(user_address)

    return reclaimable_addresses
