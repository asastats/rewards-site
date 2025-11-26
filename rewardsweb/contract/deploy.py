"""Module with functions for deploying Rewards Suite smart contract to blockchain."""

import json
from pathlib import Path

from algosdk.atomic_transaction_composer import AtomicTransactionComposer
from algosdk.v2client.algod import AlgodClient

from contract.helpers import (
    atc_method_stub,
    compile_program,
    environment_variables,
    private_key_from_mnemonic,
    read_json,
)
from contract.network import create_app, delete_app, fund_app


def delete_dapp(network, app_id):
    """Delete a deployed smart contract application.

    Creates an Algod client, retrieves the creator private key from the
    environment, and calls :func:`delete_app` to remove the application
    from the blockchain.

    :param network: The network where the dApp exists (e.g., ``"testnet"``).
    :type network: str
    :param app_id: The application ID to delete.
    :type app_id: int
    :var env: environment variables collection
    :type env: dict
    :var client: Algorand Node client instance
    :type client: :class:`AlgodClient`
    :var creator_private_key: private key of the creator used to sign deletion
    :type creator_private_key: str
    :return: None
    :rtype: None
    """
    env = environment_variables()
    client = AlgodClient(
        env.get(f"algod_token_{network}"), env.get(f"algod_address_{network}")
    )
    creator_private_key = private_key_from_mnemonic(
        env.get(f"admin_{network}_mnemonic")
    )
    delete_app(client, creator_private_key, app_id)


def deploy_app(network="testnet"):
    """Compile Rewards Suite smart contract, deploy it, and update the artifacts.

    This function orchestrates the deployment process by:
    1. Compiling the TEAL approval and clear programs
    2. Creating a new application on the specified network
    3. Capturing the new app ID and the network's genesis hash
    4. Updating the ARC-56 JSON artifact with the new network information

    :param network: network to deploy to (e.g., "testnet")
    :type network: str
    :var env: environment variables collection
    :type env: dict
    :var dapp_name: name of the smart contract application
    :type dapp_name: str
    :var client: Algorand Node client
    :type client: :class:`AlgodClient`
    :var creator_private_key: private key of the application creator
    :type creator_private_key: str
    :var approval_program_source: approval program source code
    :type approval_program_source: bytes
    :var clear_program_source: clear program source code
    :type clear_program_source: bytes
    :var contract_json: ARC-56 smart contract specification
    :type contract_json: dict
    :var approval_program: compiled approval program
    :type approval_program: str
    :var clear_program: compiled clear program
    :type clear_program: str
    :var app_id: ID of the newly created application
    :type app_id: int
    :var genesis_hash: genesis hash of the network
    :type genesis_hash: str
    :return: ID of the newly created application
    :rtype: int
    """
    env = environment_variables()

    dapp_name = env.get("rewards_dapp_name")

    client = AlgodClient(
        env.get(f"algod_token_{network}"), env.get(f"algod_address_{network}")
    )
    creator_private_key = private_key_from_mnemonic(
        env.get(f"admin_{network}_mnemonic")
    )

    approval_program_source = (
        open(
            Path(__file__).resolve().parent / "artifacts" / f"{dapp_name}.approval.teal"
        )
        .read()
        .encode()
    )
    clear_program_source = (
        open(Path(__file__).resolve().parent / "artifacts" / f"{dapp_name}.clear.teal")
        .read()
        .encode()
    )
    contract_json_path = (
        Path(__file__).resolve().parent / "artifacts" / f"{dapp_name}.arc56.json"
    )
    contract_json = read_json(contract_json_path)

    # compile programs
    approval_program = compile_program(client, approval_program_source)
    clear_program = compile_program(client, clear_program_source)

    # create new application
    app_id, genesis_hash = create_app(
        client, creator_private_key, approval_program, clear_program, contract_json
    )

    # update networks section of smart contract
    if "networks" not in contract_json:
        contract_json["networks"] = {}

    contract_json["networks"][genesis_hash] = {"appID": app_id}

    # write to file
    with open(contract_json_path, "w") as json_file:
        json.dump(contract_json, json_file, indent=4)

    # print("App ID: ", app_id)
    return app_id


def deploy_and_setup(network):
    """Deploy smart contract on `network`, fund the app's escrow, and setup application.

    :param network: network to deploy to (e.g., "testnet")
    :type network: str
    :var app_id: Rewards dApp unique identifier
    :type app_id: int
    :return: int
    """
    app_id = deploy_app(network)
    fund_app(app_id, network, amount=500_000)
    setup_app(network)
    return app_id


def setup_app(network):
    """Set up the deployed smart contract.

    :param network: network to deploy to (e.g., "testnet")
    :type network: str
    :var env: environment variables collection
    :type env: dict
    :var client: Algorand Node client
    :type client: :class:`AlgodClient`
    :var token_id: Algorand standard asset identifier to be distributed
    :type token_id: int
    :var claim_period_duration: duration of the claim period in seconds
    :type claim_period_duration: int
    :var genesis_hash: genesis hash of the network
    :type genesis_hash: str
    :var atc_stub: collection of data required to create atomic transaction
    :type atc_stub: dict
    :var atc: clear program source code
    :type atc: :class:`AtomicTransactionComposer`
    :var response: atomic transaction creation response
    :type response: :class:`AtomicTransactionResponse`
    """
    env = environment_variables()
    client = AlgodClient(
        env.get(f"algod_token_{network}"), env.get(f"algod_address_{network}")
    )
    token_id = int(env.get(f"rewards_token_id_{network}"))
    claim_period_duration = int(env.get("claim_period_duration"))
    atc_stub = atc_method_stub(client, network)
    atc = AtomicTransactionComposer()

    atc.add_method_call(
        app_id=atc_stub.get("app_id"),
        method=atc_stub.get("contract").get_method_by_name("setup"),
        sender=atc_stub.get("sender"),
        sp=atc_stub.get("sp"),
        signer=atc_stub.get("signer"),
        method_args=[token_id, claim_period_duration],
        foreign_assets=[token_id],
    )
    print("Setting up the contract...")
    response = atc.execute(client, 2)
    print(f"Contract setup complete in transaction {response.tx_ids[0]}")
