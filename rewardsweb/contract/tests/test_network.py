"""Testing module for :py:mod:`contract.network` module."""

import base64
import struct
import time

import pytest
from algosdk.error import AlgodHTTPError
from algosdk.logic import get_application_address

from contract.network import (
    ACTIVE_NETWORK,
    _add_allocations,
    _check_balances,
    _reclaim_allocation,
    claimable_amount_for_address,
    create_app,
    delete_app,
    fund_app,
    process_allocations,
    process_allocations_for_contributions,
    process_reclaim_allocation,
    reclaimable_addresses,
)


class TestContractNetworkPrivateFunctions:
    """Testing class for :py:mod:`contract.network` private functions."""

    # # _add_allocations
    def test_contract_network_add_allocations_functionality(self, mocker):
        network = "testnet"
        addresses = [
            "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU",
            "VW55KZ3NF4GDOWI7IPWLGZDFWNXWKSRD5PETRLDABZVU5XPKRJJRK3CBSU",
        ]
        amounts = [100, 200]
        token_id = 505
        app_id = 749507218

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
            "rewards_token_id_testnet": token_id,
            "rewards_token_decimals": 6,
        }

        mocked_env = mocker.patch(
            "contract.network.environment_variables", return_value=env
        )

        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.network.AlgodClient", return_value=client
        )

        stub_contract = mocker.MagicMock()
        stub_contract.get_method_by_name.return_value = "METHOD_OBJ"

        atc_stub = {
            "app_id": app_id,
            "contract": stub_contract,
            "sender": "sender_address",
            "sp": mocker.MagicMock(),
            "signer": mocker.MagicMock(),
        }

        mocked_atc_stub = mocker.patch(
            "contract.network.atc_method_stub", return_value=atc_stub
        )
        transfer = mocker.MagicMock()
        mocked_transfer = mocker.patch(
            "contract.network.AssetTransferTxn", return_value=transfer
        )
        mocked_signer = mocker.patch("contract.network.TransactionWithSigner")

        app_address = get_application_address(atc_stub["app_id"])
        atc = mocker.MagicMock()
        mocked_atc = mocker.patch(
            "contract.network.AtomicTransactionComposer", return_value=atc
        )

        response = mocker.MagicMock()
        response.tx_ids = ["TX123"]
        atc.execute.return_value = response

        mocker.patch("builtins.print")  # Silence logs

        returned = _add_allocations(network, addresses, amounts)
        assert returned == "TX123"
        microasa_amounts = [amount * 10**6 for amount in amounts]
        boxes = [
            (
                app_id,
                (
                    b"allocations\xd1*l\xf0&t\x97\xb4\xfb\x94\xc0\xc9\xa0"
                    b"\xd0\xd3l\xc3\x9c\xe5h\xef+HA\xb9\xca\xf0!\xb8k\xc6\xf7"
                ),
            ),
            (
                app_id,
                (
                    b"allocations\xad\xbb\xd5gm/\x0c7Y\x1fC\xec\xb3de\xb3oeJ#"
                    b"\xeb\xc98\xac`\x0ekN\xdd\xea\x8aS"
                ),
            ),
        ]
        mocked_env.assert_called_once_with()
        mocked_client.assert_called_once_with("token", "address")
        client.suggested_params.assert_called_with()
        assert client.suggested_params.call_count == 2
        mocked_transfer.assert_called_once_with(
            sender=atc_stub.get("sender"),
            receiver=app_address,
            amt=sum(microasa_amounts),
            index=token_id,
            sp=client.suggested_params.return_value,
        )
        mocked_signer.assert_called_once_with(
            txn=mocked_transfer.return_value,
            signer=atc_stub.get("signer"),
        )
        mocked_atc.return_value.add_transaction.assert_called_once_with(
            mocked_signer.return_value
        )
        mocked_atc_stub.assert_called_once_with(client, network)
        mocked_atc.assert_called_once_with()
        atc.add_method_call.assert_called_once_with(
            app_id=app_id,
            method="METHOD_OBJ",
            sender="sender_address",
            sp=client.suggested_params.return_value,
            signer=atc_stub["signer"],
            method_args=[addresses, microasa_amounts],
            boxes=boxes,
            foreign_assets=[token_id],
        )
        atc.execute.assert_called_once_with(client, 2)

    # # _check_balances
    def test_contract_network_check_balances_returns_algo_and_token(self, mocker):
        client = mocker.MagicMock()
        address = "ADDR123"
        token_id = 42

        client.account_info.return_value = {
            "amount": 2_000_000,
            "min-balance": 100_000,
            "assets": [
                {"asset-id": 10, "amount": 999},
                {"asset-id": 42, "amount": 1234},
            ],
        }

        returned = _check_balances(client, address, token_id)

        assert returned == (2_000_000 - 100_000, 1234)
        client.account_info.assert_called_once_with(address)

    def test_contract_network_check_balances_returns_zero_when_token_not_found(
        self, mocker
    ):
        client = mocker.MagicMock()
        address = "ADDR123"
        token_id = 999

        client.account_info.return_value = {
            "amount": 1_000_000,
            "min-balance": 0,
            "assets": [
                {"asset-id": 111, "amount": 777},
            ],
        }

        returned = _check_balances(client, address, token_id)

        assert returned == (1_000_000, 0)

    def test_contract_network_check_balances_raises_error_for_missing_account_info(
        self, mocker
    ):
        client = mocker.MagicMock()
        client.account_info.return_value = None

        with pytest.raises(ValueError, match="Can't fetch account info"):
            _check_balances(client, "ADDR", 42)

    # # _reclaim_allocation
    def test_contract_network_reclaim_allocation_functionality(self, mocker):
        network = "mainnet"
        user_address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
        token_id = 507

        env = {
            "algod_token_mainnet": "main_token",
            "algod_address_mainnet": "main_address",
            "rewards_token_id_mainnet": token_id,
            "rewards_token_decimals": 6,
        }

        mocked_env = mocker.patch(
            "contract.network.environment_variables", return_value=env
        )

        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.network.AlgodClient", return_value=client
        )

        stub_contract = mocker.MagicMock()
        stub_contract.get_method_by_name.return_value = "METHOD_OBJ"

        atc_stub = {
            "app_id": 222,
            "contract": stub_contract,
            "sender": "sender_address",
            "sp": mocker.MagicMock(),
            "signer": mocker.MagicMock(),
        }

        mocked_atc_stub = mocker.patch(
            "contract.network.atc_method_stub", return_value=atc_stub
        )

        atc = mocker.MagicMock()
        mocked_atc = mocker.patch(
            "contract.network.AtomicTransactionComposer", return_value=atc
        )

        response = mocker.MagicMock()
        response.tx_ids = ["TX777"]
        atc.execute.return_value = response

        mocker.patch("builtins.print")  # Silence logs

        returned = _reclaim_allocation(network, user_address)
        assert returned == "TX777"

        mocked_env.assert_called_once_with()
        mocked_client.assert_called_once_with("main_token", "main_address")
        mocked_atc_stub.assert_called_once_with(client, network)
        mocked_atc.assert_called_once_with()

        atc.add_method_call.assert_called_once_with(
            app_id=222,
            method="METHOD_OBJ",
            sender="sender_address",
            sp=atc_stub["sp"],
            signer=atc_stub["signer"],
            method_args=[user_address],
            boxes=[
                (
                    222,
                    (
                        b"allocations\xd1*l\xf0&t\x97\xb4\xfb\x94\xc0\xc9\xa0\xd0"
                        b"\xd3l\xc3\x9c\xe5h\xef+HA\xb9\xca\xf0!\xb8k\xc6\xf7"
                    ),
                )
            ],
            foreign_assets=[token_id],
        )

        atc.execute.assert_called_once_with(client, 2)


class TestContractNetworkPublicFunctions:
    """Testing class for :py:mod:`contract.network` public functions."""

    def test_contract_network_claimable_amount_for_address_claimable_default_network(
        self, mocker
    ):
        user_address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"

        env = {
            f"algod_token_{ACTIVE_NETWORK}": "token",
            f"algod_address_{ACTIVE_NETWORK}": "address",
            "rewards_token_decimals": 6,
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        atc_stub = {"app_id": 111}
        mocker.patch("contract.network.atc_method_stub", return_value=atc_stub)

        # amount > 0 and expires_at in the future → True
        future_timestamp = int(time.time()) + 5000
        packed = struct.pack(">QQ", 15_000_000_000, future_timestamp)
        encoded = base64.b64encode(packed)

        client.application_box_by_name.return_value = {"value": encoded}

        returned = claimable_amount_for_address(user_address)

        assert returned == 15_000

    def test_contract_network_claimable_amount_for_address_claimable(self, mocker):
        network = "mainnet"
        user_address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"

        env = {
            "algod_token_mainnet": "token",
            "algod_address_mainnet": "address",
            "rewards_token_decimals": 2,
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        atc_stub = {"app_id": 111}
        mocker.patch("contract.network.atc_method_stub", return_value=atc_stub)

        # amount > 0 and expires_at in the future → True
        future_timestamp = int(time.time()) + 5000
        packed = struct.pack(">QQ", 10_000, future_timestamp)
        encoded = base64.b64encode(packed)

        client.application_box_by_name.return_value = {"value": encoded}

        returned = claimable_amount_for_address(user_address, network)

        assert returned == 100

    def test_contract_network_claimable_amount_for_address_returns_false_for_no_box(
        self, mocker
    ):
        network = "testnet"
        user_address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)
        mocker.patch("contract.network.atc_method_stub", return_value={"app_id": 222})

        client.application_box_by_name.side_effect = AlgodHTTPError("box not found")

        returned = claimable_amount_for_address(user_address, network)

        assert returned is False

    def test_contract_network_claimable_amount_for_address_returns_false_when_box_missing(
        self, mocker
    ):
        network = "testnet"
        user_address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)
        mocker.patch("contract.network.atc_method_stub", return_value={"app_id": 222})

        client.application_box_by_name.return_value = {"value": None}

        returned = claimable_amount_for_address(user_address, network)

        assert returned is False

    def test_contract_network_claimable_amount_for_address_returns_false_when_amount_zero(
        self, mocker
    ):
        network = "testnet"
        user_address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)
        mocker.patch("contract.network.atc_method_stub", return_value={"app_id": 333})

        # amount = 0 → returns False
        future_timestamp = int(time.time()) + 100
        packed = struct.pack(">QQ", 0, future_timestamp)
        encoded = base64.b64encode(packed)

        client.application_box_by_name.return_value = {"value": encoded}

        returned = claimable_amount_for_address(user_address, network)

        assert returned is False

    def test_contract_network_claimable_amount_for_address_raises_when_expired(
        self, mocker
    ):
        network = "mainnet"
        user_address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"

        env = {
            "algod_token_mainnet": "token",
            "algod_address_mainnet": "address",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)
        mocker.patch("contract.network.atc_method_stub", return_value={"app_id": 444})

        # amount > 0 but expired → raises ValueError
        past_timestamp = int(time.time()) - 999
        packed = struct.pack(">QQ", 999, past_timestamp)
        encoded = base64.b64encode(packed)

        client.application_box_by_name.return_value = {"value": encoded}

        with pytest.raises(ValueError, match="claim period has ended"):
            claimable_amount_for_address(user_address, network)

    # # create_app
    def test_contract_network_create_app_calls_wait_and_returns_app_id(self, mocker):
        client = mocker.MagicMock()
        private_key = mocker.MagicMock()
        approval_program = mocker.MagicMock()
        clear_program = mocker.MagicMock()
        contract_json = mocker.MagicMock()

        sender_address = mocker.MagicMock()
        mocker.patch(
            "contract.network.address_from_private_key", return_value=sender_address
        )

        mock_txn = mocker.MagicMock()
        mock_signed = mocker.MagicMock()
        mock_signed.transaction.get_txid.return_value = "txid123"
        mocker.patch(
            "contract.network.transaction.ApplicationCreateTxn", return_value=mock_txn
        )
        mock_txn.sign.return_value = mock_signed

        mocked_wait = mocker.patch("contract.network.wait_for_confirmation")
        client.pending_transaction_info.return_value = {"application-index": 99}
        mock_params = mocker.MagicMock()
        mock_params.gh = b"genesis_hash_value"
        client.suggested_params.return_value = mock_params

        returned_app_id, returned_genesis_hash = create_app(
            client, private_key, approval_program, clear_program, contract_json
        )

        assert returned_app_id == 99
        assert returned_genesis_hash == b"genesis_hash_value"
        mock_txn.sign.assert_called_once_with(private_key)
        client.send_transactions.assert_called_once_with([mock_signed])
        mocked_wait.assert_called_once_with(client, "txid123")

    # # delete_app
    def test_contract_network_delete_app_calls_wait(self, mocker):
        client = mocker.MagicMock()
        private_key = mocker.MagicMock()
        index = 2000

        sender_address = mocker.MagicMock()
        mocker.patch(
            "contract.network.address_from_private_key", return_value=sender_address
        )

        mock_txn = mocker.MagicMock()
        mock_signed = mocker.MagicMock()
        mock_signed.transaction.get_txid.return_value = "txid123"
        mocker.patch(
            "contract.network.transaction.ApplicationDeleteTxn", return_value=mock_txn
        )
        mock_txn.sign.return_value = mock_signed

        mocked_wait = mocker.patch("contract.network.wait_for_confirmation")

        client.pending_transaction_info.return_value = {"txn": {"txn": {"apid": index}}}

        delete_app(client, private_key, index)

        mock_txn.sign.assert_called_once_with(private_key)
        client.send_transactions.assert_called_once_with([mock_signed])
        mocked_wait.assert_called_once_with(client, "txid123")

    # # fund_app
    def test_contract_network_fund_app_for_provided_amount(self, mocker):
        app_id = 5059
        network = "testnet"
        amount = 500_000

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
            "admin_testnet_mnemonic": "mnemonic",
        }

        mocked_env = mocker.patch(
            "contract.network.environment_variables", return_value=env
        )

        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.network.AlgodClient", return_value=client
        )

        creator_private_key = mocker.MagicMock()
        mocked_private_key = mocker.patch(
            "contract.network.private_key_from_mnemonic",
            return_value=creator_private_key,
        )

        sender = "sender-address"
        mocked_address = mocker.patch(
            "contract.network.address_from_private_key",
            return_value=sender,
        )

        app_address = "app-escrow-address"
        mocked_app_address = mocker.patch(
            "contract.network.get_application_address", return_value=app_address
        )

        suggested_params = mocker.MagicMock()
        client.suggested_params.return_value = suggested_params

        mock_tx = mocker.MagicMock()
        mock_signed = mocker.MagicMock()
        mock_signed.transaction.get_txid.return_value = "tx123"

        mocked_payment = mocker.patch(
            "contract.network.PaymentTxn", return_value=mock_tx
        )
        mock_tx.sign.return_value = mock_signed

        mocked_wait = mocker.patch("contract.network.wait_for_confirmation")
        mocker.patch("builtins.print")  # suppress output

        fund_app(app_id, network, amount=amount)

        mocked_env.assert_called_once_with()
        mocked_client.assert_called_once_with("token", "address")
        mocked_private_key.assert_called_once_with("mnemonic")
        mocked_address.assert_called_once_with(creator_private_key)
        mocked_app_address.assert_called_once_with(app_id)

        mocked_payment.assert_called_once_with(
            sender=sender,
            sp=suggested_params,
            receiver=app_address,
            amt=amount,
        )

        client.send_transactions.assert_called_once_with([mock_signed])
        mocked_wait.assert_called_once_with(client, "tx123")

    def test_contract_network_fund_app_for_no_env_variable(self, mocker):
        app_id = 5059
        network = "testnet"

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
            "admin_testnet_mnemonic": "mnemonic",
        }

        mocked_env = mocker.patch(
            "contract.network.environment_variables", return_value=env
        )

        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.network.AlgodClient", return_value=client
        )

        creator_private_key = mocker.MagicMock()
        mocked_private_key = mocker.patch(
            "contract.network.private_key_from_mnemonic",
            return_value=creator_private_key,
        )

        sender = "sender-address"
        mocked_address = mocker.patch(
            "contract.network.address_from_private_key",
            return_value=sender,
        )

        app_address = "app-escrow-address"
        mocked_app_address = mocker.patch(
            "contract.network.get_application_address", return_value=app_address
        )

        suggested_params = mocker.MagicMock()
        client.suggested_params.return_value = suggested_params

        mock_tx = mocker.MagicMock()
        mock_signed = mocker.MagicMock()
        mock_signed.transaction.get_txid.return_value = "tx123"

        mocked_payment = mocker.patch(
            "contract.network.PaymentTxn", return_value=mock_tx
        )
        mock_tx.sign.return_value = mock_signed

        mocked_wait = mocker.patch("contract.network.wait_for_confirmation")
        mocker.patch("builtins.print")  # suppress output

        fund_app(app_id, network)

        mocked_env.assert_called_once_with()
        mocked_client.assert_called_once_with("token", "address")
        mocked_private_key.assert_called_once_with("mnemonic")
        mocked_address.assert_called_once_with(creator_private_key)
        mocked_app_address.assert_called_once_with(app_id)

        mocked_payment.assert_called_once_with(
            sender=sender,
            sp=suggested_params,
            receiver=app_address,
            amt=100000,
        )

        client.send_transactions.assert_called_once_with([mock_signed])
        mocked_wait.assert_called_once_with(client, "tx123")

    def test_contract_network_fund_app_functionality(self, mocker):
        app_id = 5059
        network = "testnet"

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
            "admin_testnet_mnemonic": "mnemonic",
            "dapp_minimum_algo": 250_000,
        }

        mocked_env = mocker.patch(
            "contract.network.environment_variables", return_value=env
        )

        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.network.AlgodClient", return_value=client
        )

        creator_private_key = mocker.MagicMock()
        mocked_private_key = mocker.patch(
            "contract.network.private_key_from_mnemonic",
            return_value=creator_private_key,
        )

        sender = "sender-address"
        mocked_address = mocker.patch(
            "contract.network.address_from_private_key",
            return_value=sender,
        )

        app_address = "app-escrow-address"
        mocked_app_address = mocker.patch(
            "contract.network.get_application_address", return_value=app_address
        )

        suggested_params = mocker.MagicMock()
        client.suggested_params.return_value = suggested_params

        mock_tx = mocker.MagicMock()
        mock_signed = mocker.MagicMock()
        mock_signed.transaction.get_txid.return_value = "tx123"

        mocked_payment = mocker.patch(
            "contract.network.PaymentTxn", return_value=mock_tx
        )
        mock_tx.sign.return_value = mock_signed

        mocked_wait = mocker.patch("contract.network.wait_for_confirmation")
        mocker.patch("builtins.print")  # suppress output

        fund_app(app_id, network)

        mocked_env.assert_called_once_with()
        mocked_client.assert_called_once_with("token", "address")
        mocked_private_key.assert_called_once_with("mnemonic")
        mocked_address.assert_called_once_with(creator_private_key)
        mocked_app_address.assert_called_once_with(app_id)

        mocked_payment.assert_called_once_with(
            sender=sender,
            sp=suggested_params,
            receiver=app_address,
            amt=250_000,
        )

        client.send_transactions.assert_called_once_with([mock_signed])
        mocked_wait.assert_called_once_with(client, "tx123")

    # # process_allocations
    def test_contract_network_process_allocations_happy_path(self, mocker):
        network = "testnet"
        addresses = ["A1", "A2"]
        amounts = [5, 10]
        token_id = 1111

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
            "rewards_token_id_testnet": token_id,
            "dapp_minimum_algo": 100000,
            "rewards_token_decimals": 6,
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        stub = {
            "sender": "ADMIN_ADDR",
            "app_id": 123,
        }
        mocker.patch("contract.network.atc_method_stub", return_value=stub)
        mocker.patch(
            "contract.network.get_application_address", return_value="APP_ADDR"
        )

        mock_check = mocker.patch(
            "contract.network._check_balances",
            side_effect=[
                (200_000, 0),  # app_algo_balance (sufficient)
                (150_000, 16 * 10**6),  # admin balances
            ],
        )

        mocked_fund = mocker.patch("contract.network.fund_app")
        mocked_add = mocker.patch("contract.network._add_allocations")

        returned = process_allocations(network, addresses, amounts)
        assert returned == mocked_add.return_value

        mocked_fund.assert_not_called()
        mocked_add.assert_called_once_with(network, addresses, amounts)

        assert mock_check.call_count == 2

    def test_contract_network_process_allocations_funds_app_if_needed(self, mocker):
        network = "testnet"
        addresses = ["A1"]
        amounts = [5]
        token_id = 1111

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
            "rewards_token_id_testnet": token_id,
            "dapp_minimum_algo": 200000,
            "rewards_token_decimals": 6,
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        stub = {"sender": "ADMIN_ADDR", "app_id": 123}
        mocker.patch("contract.network.atc_method_stub", return_value=stub)
        mocker.patch(
            "contract.network.get_application_address", return_value="APP_ADDR"
        )

        mock_check = mocker.patch(
            "contract.network._check_balances",
            side_effect=[
                (50_000, 0),  # app balance insufficient
                (300_000, 0),  # admin algo enough to fund
                (300_000, 11 * 10**6),  # admin token after funding
            ],
        )

        mocked_fund = mocker.patch("contract.network.fund_app")
        mocked_add = mocker.patch("contract.network._add_allocations")

        returned = process_allocations(network, addresses, amounts)
        assert returned == mocked_add.return_value

        mocked_fund.assert_called_once_with(123, network)  # ✅ app funded
        mocked_add.assert_called_once_with(network, addresses, amounts)
        assert mock_check.call_count == 3

    def test_contract_network_process_allocations_not_enough_algo(self, mocker):
        network = "testnet"
        addresses = ["A1"]
        amounts = [50000]
        token_id = 1111

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
            "rewards_token_id_testnet": token_id,
            "dapp_minimum_algo": 200000,
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        stub = {"sender": "ADMIN_ADDR", "app_id": 123}
        mocker.patch("contract.network.atc_method_stub", return_value=stub)
        mocker.patch(
            "contract.network.get_application_address", return_value="APP_ADDR"
        )

        mock_check = mocker.patch(
            "contract.network._check_balances",
            side_effect=[
                (50_000, 0),  # app balance insufficient
                (40_000, 0),  # admin algo not enough to fund
            ],
        )

        mocked_fund = mocker.patch("contract.network.fund_app")
        mocked_add = mocker.patch("contract.network._add_allocations")

        with pytest.raises(ValueError, match="Not enough ALGO"):
            process_allocations(network, addresses, amounts)

        mocked_fund.assert_not_called()
        mocked_add.assert_not_called()
        assert mock_check.call_count == 2

    def test_contract_network_process_allocations_not_enough_tokens(self, mocker):
        network = "testnet"
        addresses = ["A1"]
        amounts = [500]
        token_id = 1111

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
            "rewards_token_id_testnet": token_id,
            "dapp_minimum_algo": 100000,
            "rewards_token_decimals": 6,
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        stub = {"sender": "ADMIN_ADDR", "app_id": 123}
        mocker.patch("contract.network.atc_method_stub", return_value=stub)
        mocker.patch(
            "contract.network.get_application_address", return_value="APP_ADDR"
        )

        mocker.patch(
            "contract.network._check_balances",
            side_effect=[
                (500_000, 0),  # app algo ok
                (0, 19 * 10**6),  # admin doesn't have enough tokens
            ],
        )

        mocker.patch("contract.network.fund_app")
        mocker.patch("contract.network._add_allocations")

        with pytest.raises(ValueError, match="Not enough token"):
            process_allocations(network, addresses, amounts)

    # process_allocations_for_contributions
    def test_contract_network_process_allocations_for_contributions_no_addresses(
        self, mocker
    ):
        contributions = mocker.MagicMock()
        allocations_callback = mocker.MagicMock()
        allocations_callback.return_value = ([], [])
        mocked_process = mocker.patch("contract.network.process_allocations")

        results = list(
            process_allocations_for_contributions(contributions, allocations_callback)
        )

        assert results == [(False, [])]
        allocations_callback.assert_called_once_with(contributions)
        mocked_process.assert_not_called()

    def test_contract_allocations_for_contributions_single_batch_success(self, mocker):
        contributions = mocker.MagicMock()
        addresses = ["addr1", "addr2"]
        amounts = [100, 200]
        allocations_callback = mocker.MagicMock()
        allocations_callback.return_value = (addresses, amounts)

        # Mock batch size larger than addresses count
        mocker.patch("contract.network.ADD_ALLOCATIONS_BATCH_SIZE", 10)

        mocked_process = mocker.patch(
            "contract.network.process_allocations", return_value="tx_hash_123"
        )

        results = list(
            process_allocations_for_contributions(contributions, allocations_callback)
        )

        # Should yield: (result, batch_addresses)
        assert results == [("tx_hash_123", ["addr1", "addr2"])]
        allocations_callback.assert_called_once_with(contributions)
        mocked_process.assert_called_once_with(ACTIVE_NETWORK, addresses, amounts)

    def test_contract_network_process_allocations_for_contributions_multiple_success(
        self, mocker
    ):
        contributions = mocker.MagicMock()
        addresses = ["addr1", "addr2", "addr3", "addr4", "addr5"]
        amounts = [100, 200, 300, 400, 500]
        allocations_callback = mocker.MagicMock()
        allocations_callback.return_value = (addresses, amounts)

        # Mock batch size of 2
        mocker.patch("contract.network.ADD_ALLOCATIONS_BATCH_SIZE", 2)

        # Mock process_allocations to return different results for each batch
        batch_results = ["tx_hash_1", "tx_hash_2", "tx_hash_3"]
        mocked_process = mocker.patch(
            "contract.network.process_allocations", side_effect=batch_results
        )

        results = list(
            process_allocations_for_contributions(contributions, allocations_callback)
        )

        # Expected results with batch addresses for each batch
        expected_results = [
            ("tx_hash_1", ["addr1", "addr2"]),  # Batch 1
            ("tx_hash_2", ["addr3", "addr4"]),  # Batch 2
            ("tx_hash_3", ["addr5"]),  # Batch 3
        ]

        assert results == expected_results
        allocations_callback.assert_called_once_with(contributions)
        assert mocked_process.call_count == 3

        # Verify the batch calls
        expected_calls = [
            mocker.call(ACTIVE_NETWORK, ["addr1", "addr2"], [100, 200]),
            mocker.call(ACTIVE_NETWORK, ["addr3", "addr4"], [300, 400]),
            mocker.call(ACTIVE_NETWORK, ["addr5"], [500]),
        ]
        mocked_process.assert_has_calls(expected_calls)

    def test_contract_network_process_allocations_for_contributions_batch_exception(
        self, mocker
    ):
        contributions = mocker.MagicMock()
        addresses = ["addr1", "addr2", "addr3", "addr4"]
        amounts = [100, 200, 300, 400]
        allocations_callback = mocker.MagicMock()
        allocations_callback.return_value = (addresses, amounts)

        mocker.patch("contract.network.ADD_ALLOCATIONS_BATCH_SIZE", 2)

        # First call succeeds, second call raises exception
        mocked_process = mocker.patch(
            "contract.network.process_allocations",
            side_effect=["tx_hash_1", ValueError("Transaction failed")],
        )

        results = list(
            process_allocations_for_contributions(contributions, allocations_callback)
        )

        # First batch succeeds, second batch returns (False, []) due to exception
        expected_results = [
            ("tx_hash_1", ["addr1", "addr2"]),  # Batch 1 (success)
            (False, ["Transaction failed"]),  # Batch 2 (failed)
        ]

        assert results == expected_results
        allocations_callback.assert_called_once_with(contributions)
        assert mocked_process.call_count == 2

    def test_contract_network_process_allocations_for_contributions_all_batches_fail(
        self, mocker
    ):
        contributions = mocker.MagicMock()
        addresses = ["addr1", "addr2", "addr3"]
        amounts = [100, 200, 300]
        allocations_callback = mocker.MagicMock()
        allocations_callback.return_value = (addresses, amounts)

        mocker.patch("contract.network.ADD_ALLOCATIONS_BATCH_SIZE", 1)

        mocked_process = mocker.patch(
            "contract.network.process_allocations",
            side_effect=ValueError("Transaction failed"),
        )

        results = list(
            process_allocations_for_contributions(contributions, allocations_callback)
        )

        expected_results = [(False, ["Transaction failed"])]

        assert results == expected_results
        allocations_callback.assert_called_once_with(contributions)
        mocked_process.assert_called_once_with(ACTIVE_NETWORK, ["addr1"], [100])

    def test_contract_network_process_allocations_for_contributions_exact_batch_size(
        self, mocker
    ):
        """Test when number of addresses exactly matches batch size"""
        contributions = mocker.MagicMock()
        addresses = ["addr1", "addr2", "addr3", "addr4"]
        amounts = [100, 200, 300, 400]
        allocations_callback = mocker.MagicMock()
        allocations_callback.return_value = (addresses, amounts)

        mocker.patch("contract.network.ADD_ALLOCATIONS_BATCH_SIZE", 4)

        mocked_process = mocker.patch(
            "contract.network.process_allocations", return_value="tx_hash_123"
        )

        results = list(
            process_allocations_for_contributions(contributions, allocations_callback)
        )

        # Single batch with all addresses
        assert results == [("tx_hash_123", ["addr1", "addr2", "addr3", "addr4"])]
        allocations_callback.assert_called_once_with(contributions)
        mocked_process.assert_called_once_with(ACTIVE_NETWORK, addresses, amounts)

    def test_contract_network_process_allocations_for_contributions_mixed_success_fail(
        self, mocker
    ):
        """Test mixed scenario with success, failure, and success"""
        contributions = mocker.MagicMock()
        addresses = ["addr1", "addr2", "addr3", "addr4", "addr5"]
        amounts = [100, 200, 300, 400, 500]
        allocations_callback = mocker.MagicMock()
        allocations_callback.return_value = (addresses, amounts)

        mocker.patch("contract.network.ADD_ALLOCATIONS_BATCH_SIZE", 2)

        # Mixed results: success, failure, success
        mocked_process = mocker.patch(
            "contract.network.process_allocations",
            side_effect=["tx_hash_1", "tx_hash_2", ValueError("Failed")],
        )

        results = list(
            process_allocations_for_contributions(contributions, allocations_callback)
        )

        expected_results = [
            ("tx_hash_1", ["addr1", "addr2"]),  # Batch 1 (success)
            ("tx_hash_2", ["addr3", "addr4"]),  # Batch 2 (success)
            (False, ["Failed"]),
        ]

        assert results == expected_results
        allocations_callback.assert_called_once_with(contributions)
        assert mocked_process.call_count == 3

    # # process_reclaim_allocation
    def test_contract_network_process_reclaim_allocation_calls_reclaim(self, mocker):
        user_address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        atc_stub = {"app_id": 123}
        mocker.patch("contract.network.atc_method_stub", return_value=atc_stub)

        # simulate box value (amount=100, expires_at = past timestamp)
        past_timestamp = int(time.time()) - 1000
        encoded = base64.b64encode(struct.pack(">QQ", 100, past_timestamp))

        client.application_box_by_name.return_value = {"value": encoded}

        mocked_reclaim = mocker.patch("contract.network._reclaim_allocation")

        returned = process_reclaim_allocation(user_address)
        assert returned == mocked_reclaim.return_value

        client.application_box_by_name.assert_called_once_with(
            123,
            (
                b"allocations\xd1*l\xf0&t\x97\xb4\xfb\x94\xc0\xc9\xa0"
                b"\xd0\xd3l\xc3\x9c\xe5h\xef+HA\xb9\xca\xf0!\xb8k\xc6\xf7"
            ),
        )
        mocked_reclaim.assert_called_once_with(ACTIVE_NETWORK, user_address)

    def test_contract_network_process_reclaim_allocation_raises_for_missing_box(
        self, mocker
    ):
        network = "testnet"
        user_address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        atc_stub = {"app_id": 123}
        mocker.patch("contract.network.atc_method_stub", return_value=atc_stub)

        client.application_box_by_name.return_value = {"value": None}

        with pytest.raises(ValueError, match="No user's box"):
            process_reclaim_allocation(user_address, network)

    def test_contract_network_process_reclaim_allocation_raises_when_claim_period_not_over(
        self, mocker
    ):
        network = "mainnet"
        user_address = "VW55KZ3NF4GDOWI7IPWLGZDFWNXWKSRD5PETRLDABZVU5XPKRJJRK3CBSU"

        env = {
            "algod_token_mainnet": "token",
            "algod_address_mainnet": "address",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        atc_stub = {"app_id": 999}
        mocker.patch("contract.network.atc_method_stub", return_value=atc_stub)

        # simulate future timestamp (claim not expired)
        future_timestamp = int(time.time()) + 9999
        encoded = base64.b64encode(struct.pack(">QQ", 50, future_timestamp))

        client.application_box_by_name.return_value = {"value": encoded}

        with pytest.raises(ValueError, match="User claim period hasn't ended"):
            process_reclaim_allocation(user_address, network)

    def test_contract_network_process_reclaim_allocation_not_calling_reclaim_no_amount(
        self, mocker
    ):
        network = "testnet"
        user_address = "VW55KZ3NF4GDOWI7IPWLGZDFWNXWKSRD5PETRLDABZVU5XPKRJJRK3CBSU"

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        atc_stub = {"app_id": 999}
        mocker.patch("contract.network.atc_method_stub", return_value=atc_stub)

        # amount = 0 (nothing to reclaim)
        past_timestamp = int(time.time()) - 9999
        encoded = base64.b64encode(struct.pack(">QQ", 0, past_timestamp))

        client.application_box_by_name.return_value = {"value": encoded}

        mocked_reclaim = mocker.patch("contract.network._reclaim_allocation")

        process_reclaim_allocation(user_address, network)

        mocked_reclaim.assert_not_called()

    # # reclaimable_addresses
    def test_contract_network_reclaimable_addresses_returns_only_expired_with_amount(
        self, mocker
    ):
        network = "mainnet"

        env = {
            "algod_token_mainnet": "token",
            "algod_address_mainnet": "address",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.network.AlgodClient", return_value=client
        )

        atc_stub = {"app_id": 123}
        mocker.patch("contract.network.atc_method_stub", return_value=atc_stub)

        # Simulate three application boxes
        box1 = {
            "name": "YWxsb2NhdGlvbnPRKmzwJnSXtPuUwMmg0NNsw5zlaO8rSEG5yvAhuGvG9w=="
        }  # expired, amount > 0 → reclaimable
        box2 = {
            "name": "YWxsb2NhdGlvbnOtu9VnbS8MN1kfQ+yzZGWzb2VKI+vJOKxgDmtO3eqKUw=="
        }  # expired, amount == 0 → not reclaimable
        box3 = {
            "name": "YWxsb2NhdGlvbnNd07h6OdTT6okjKyTOZq3GME4qsl7bqeI629bRJEi4WQ=="
        }  # not expired → not reclaimable

        client.application_boxes.return_value = {"boxes": [box1, box2, box3]}

        now = int(time.time())

        encoded_data = [
            struct.pack(">QQ", 100, now - 50),  # expired & reclaimable
            struct.pack(">QQ", 0, now - 50),  # expired but no amount
            struct.pack(">QQ", 10, now + 10000),  # not expired
        ]

        client.application_box_by_name.side_effect = [
            {"value": base64.b64encode(encoded_data[0])},
            {"value": base64.b64encode(encoded_data[1])},
            {"value": base64.b64encode(encoded_data[2])},
        ]

        returned = reclaimable_addresses(network)

        assert returned == [
            "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
        ]
        assert len(returned) == 1
        mocked_client.assert_called_once_with("token", "address")

    def test_contract_network_reclaimable_addresses_for_default_network(self, mocker):
        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
            "algod_token_mainnet": "token-mainnet",
            "algod_address_mainnet": "address-mainnet",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocked_client = mocker.patch(
            "contract.network.AlgodClient", return_value=client
        )

        atc_stub = {"app_id": 123}
        mocker.patch("contract.network.atc_method_stub", return_value=atc_stub)

        # Simulate three application boxes
        box1 = {
            "name": "YWxsb2NhdGlvbnPRKmzwJnSXtPuUwMmg0NNsw5zlaO8rSEG5yvAhuGvG9w=="
        }  # expired, amount > 0 → reclaimable
        box2 = {
            "name": "YWxsb2NhdGlvbnOtu9VnbS8MN1kfQ+yzZGWzb2VKI+vJOKxgDmtO3eqKUw=="
        }  # expired, amount == 0 → not reclaimable
        box3 = {
            "name": "YWxsb2NhdGlvbnNd07h6OdTT6okjKyTOZq3GME4qsl7bqeI629bRJEi4WQ=="
        }  # not expired → not reclaimable

        client.application_boxes.return_value = {"boxes": [box1, box2, box3]}

        now = int(time.time())

        encoded_data = [
            struct.pack(">QQ", 100, now - 50),  # expired & reclaimable
            struct.pack(">QQ", 0, now - 50),  # expired but no amount
            struct.pack(">QQ", 10, now + 10000),  # not expired
        ]

        client.application_box_by_name.side_effect = [
            {"value": base64.b64encode(encoded_data[0])},
            {"value": base64.b64encode(encoded_data[1])},
            {"value": base64.b64encode(encoded_data[2])},
        ]

        returned = reclaimable_addresses()

        assert returned == [
            "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
        ]
        assert len(returned) == 1
        mocked_client.assert_called_once_with("token", "address")
        client.application_boxes.assert_called_once_with(123)
        calls = [
            mocker.call(
                123,
                (
                    b"allocations\xd1*l\xf0&t\x97\xb4\xfb\x94\xc0\xc9\xa0"
                    b"\xd0\xd3l\xc3\x9c\xe5h\xef+HA\xb9\xca\xf0!\xb8k\xc6\xf7"
                ),
            ),
            mocker.call(
                123,
                (
                    b"allocations\xad\xbb\xd5gm/\x0c7Y\x1fC\xec\xb3de"
                    b"\xb3oeJ#\xeb\xc98\xac`\x0ekN\xdd\xea\x8aS"
                ),
            ),
            mocker.call(
                123,
                (
                    b"allocations]\xd3\xb8z9\xd4\xd3\xea\x89#+$\xcef\xad"
                    b"\xc60N*\xb2^\xdb\xa9\xe2:\xdb\xd6\xd1$H\xb8Y"
                ),
            ),
        ]
        client.application_box_by_name.assert_has_calls(calls, any_order=True)
        assert client.application_box_by_name.call_count == 3

    def test_contract_network_reclaimable_addresses_returns_empty_when_no_boxes(
        self, mocker
    ):
        network = "testnet"

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        atc_stub = {"app_id": 999}
        mocker.patch("contract.network.atc_method_stub", return_value=atc_stub)

        client.application_boxes.return_value = {"boxes": []}

        returned = reclaimable_addresses(network)

        assert returned == []

    def test_contract_network_reclaimable_addresses_ignores_missing_box_value(
        self, mocker
    ):
        network = "testnet"

        env = {
            "algod_token_testnet": "token",
            "algod_address_testnet": "address",
        }
        mocker.patch("contract.network.environment_variables", return_value=env)

        client = mocker.MagicMock()
        mocker.patch("contract.network.AlgodClient", return_value=client)

        atc_stub = {"app_id": 999}
        mocker.patch("contract.network.atc_method_stub", return_value=atc_stub)

        box = {"name": "YWxsb2NhdGlvbnOtu9VnbS8MN1kfQ+yzZGWzb2VKI+vJOKxgDmtO3eqKUw=="}
        client.application_boxes.return_value = {"boxes": [box]}

        # Application box returns None for "value"
        client.application_box_by_name.return_value = {"value": None}

        # struct.unpack should not be called; simply skip box
        returned = reclaimable_addresses(network)

        assert returned == []
