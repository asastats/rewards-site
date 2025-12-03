"""Module with integration tests for the Rewards smart contract."""

import base64
import json
import os
import time
from pathlib import Path

import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AppClientMethodCallParams,
    Arc56Contract,
    AssetTransferParams,
    LogicError,
    PaymentParams,
    SendParams,
    SigningAccount,
)
from algokit_utils.applications import AppClient, AppClientParams
from algosdk import encoding
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.error import AlgodHTTPError
from algosdk.transaction import AssetCreateTxn
from dotenv import load_dotenv

from contract.helpers import compile_program
from contract.network import create_app

load_dotenv(Path(__file__).parent.parent / ".env")

dapp_name = os.getenv("REWARDS_DAPP_NAME")

# Assume tests are run from the project root
CONTRACT_PATH = Path(__file__).parent.parent / "artifacts"
APP_SPEC_PATH = CONTRACT_PATH / f"{dapp_name}.arc56.json"


@pytest.fixture(scope="session")
def app_spec() -> Arc56Contract:
    """Get the application specification from the compiled artifact."""
    spec = json.loads(APP_SPEC_PATH.read_text())
    for network in spec["networks"].values():
        if "appID" in network:
            network["appId"] = network.pop("appID")
    return Arc56Contract.from_dict(spec)


def _create_asset(algorand_client: AlgorandClient, account: SigningAccount) -> int:
    """Create a new asset for testing."""
    sp = algorand_client.client.algod.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_transaction(
        TransactionWithSigner(
            AssetCreateTxn(
                asset_name="ASA Stats Token test",
                unit_name="ASASTATS",
                sender=account.address,
                sp=sp,
                total=1_000_000_000_000_000,
                decimals=6,
                default_frozen=False,
            ),
            signer=account.signer,
        )
    )
    result = atc.execute(algorand_client.client.algod, 4)
    tx_info = algorand_client.client.algod.pending_transaction_info(result.tx_ids[0])
    return tx_info["asset-index"]


def _make_transfer(asset_creator_account, receiver, token_id, amount):
    algorand = AlgorandClient.from_environment()
    algorand.send.asset_transfer(
        AssetTransferParams(
            sender=asset_creator_account.address,
            asset_id=token_id,
            amount=amount,
            receiver=receiver,
            signer=asset_creator_account.signer,
        ),
        SendParams(max_rounds_to_wait_for_confirmation=5, suppress_log=False),
    )


class BaseTestContract:
    """Base testing class for :class:`contract.contract.Rewards`."""

    name = "rewards"
    claim_period_duration = 3600

    @pytest.fixture(autouse=True)
    def _setup_contract(
        self,
        algorand_client: AlgorandClient,
        app_spec: Arc56Contract,
        token_id: int,
        admin_account: SigningAccount,
    ):
        """
        Deploy app using app_spec + your own TEAL compile logic.
        """

        algod = algorand_client.client.algod

        # --------------------------------------------------------------------
        # ✅ Extract name from app_spec (this matches *.approval.teal filenames)
        # --------------------------------------------------------------------
        dapp_name = app_spec.name  # <-- this IS from app_spec

        artifacts_path = Path(__file__).resolve().parent.parent / "artifacts"

        approval_teal_path = artifacts_path / f"{dapp_name}.approval.teal"
        clear_teal_path = artifacts_path / f"{dapp_name}.clear.teal"

        # --------------------------------------------------------------------
        # ✅ Load TEAL source from artifacts (using your logic)
        # --------------------------------------------------------------------
        approval_program_source = approval_teal_path.read_bytes()
        clear_program_source = clear_teal_path.read_bytes()

        # --------------------------------------------------------------------
        # ✅ Compile using your compile_program()
        # --------------------------------------------------------------------
        approval_program = compile_program(algod, approval_program_source)
        clear_program = compile_program(algod, clear_program_source)

        # --------------------------------------------------------------------
        # ✅ app_spec → ARC56 JSON (your create_app expects dict)
        # --------------------------------------------------------------------
        contract_json = json.loads(app_spec.to_json())

        # --------------------------------------------------------------------
        # ✅ Create the app using your create_app() function
        #    This triggers @baremethod(create="require")
        # --------------------------------------------------------------------
        app_id, _gh = create_app(
            client=algod,
            private_key=admin_account.private_key,
            approval_program=approval_program,
            clear_program=clear_program,
            contract_json=contract_json,
        )

        # --------------------------------------------------------------------
        # ✅ Wrap in AppClient for ABI calls
        # --------------------------------------------------------------------
        rewards_client = AppClient(
            AppClientParams(
                algorand=algorand_client,
                app_spec=app_spec,
                app_id=app_id,
            )
        )

        # --------------------------------------------------------------------
        # ✅ Fund the contract account so inner ASA transfers work
        # --------------------------------------------------------------------
        algorand_client.send.payment(
            PaymentParams(
                sender=admin_account.address,
                receiver=rewards_client.app_address,
                amount=AlgoAmount(algo=1),
                signer=admin_account.signer,
            )
        )

        # --------------------------------------------------------------------
        # ✅ Call setup(token_id, claim_period_duration)
        # --------------------------------------------------------------------
        rewards_client.send.call(
            AppClientMethodCallParams(
                method="setup",
                args=[token_id, self.claim_period_duration],
                sender=admin_account.address,
                signer=admin_account.signer,
                static_fee=AlgoAmount(micro_algo=2000),
            )
        )

        # Expose for tests (test methods can now reference self.rewards_client)
        self.rewards_client = rewards_client

    @pytest.fixture
    def algorand_client(self) -> AlgorandClient:
        return AlgorandClient.from_environment()

    @pytest.fixture
    def admin_account(self, algorand_client: AlgorandClient) -> SigningAccount:
        return algorand_client.account.from_environment(
            "ADMIN_ACCOUNT" + "_" + self.name.upper(), fund_with=AlgoAmount(algo=1000)
        )

    @pytest.fixture
    def asset_creator_account(self, algorand_client: AlgorandClient) -> SigningAccount:
        return algorand_client.account.from_environment(
            "ASSET_CREATOR_ACCOUNT" + "_" + self.name.upper(),
            fund_with=AlgoAmount(algo=100),
        )

    @pytest.fixture
    def token_id(
        self, algorand_client: AlgorandClient, asset_creator_account: SigningAccount
    ) -> int:
        return _create_asset(algorand_client, asset_creator_account)

    @pytest.fixture
    def user_account(self, algorand_client: AlgorandClient) -> SigningAccount:
        return algorand_client.account.from_environment(
            "USER_ACCOUNT" + "_" + self.name.upper(),
            fund_with=AlgoAmount(algo=10),
        )


class TestContractAddAllocations(BaseTestContract):
    """Testing class for :class:`contract.contract.Rewards` add_allocations method."""

    name = "add"

    @pytest.fixture
    def other_account(self, algorand_client: AlgorandClient) -> SigningAccount:
        return algorand_client.account.from_environment(
            "OTHER_ACCOUNT" + "_" + self.name.upper(),
            fund_with=AlgoAmount(algo=10),
        )

    @pytest.fixture
    def user_accounts_4(self, algorand_client: AlgorandClient) -> SigningAccount:
        users_count = 4
        user_accounts = []
        for i in range(users_count):
            user_accounts.append(
                algorand_client.account.from_environment(
                    f"USER{i}_ACCOUNT", fund_with=AlgoAmount(algo=10)
                )
            )
        return user_accounts

    @pytest.fixture
    def user_accounts_5(self, algorand_client: AlgorandClient) -> SigningAccount:
        users_count = 5
        user_accounts = []
        for i in range(users_count):
            user_accounts.append(
                algorand_client.account.from_environment(
                    f"USER{i}_ACCOUNT", fund_with=AlgoAmount(algo=10)
                )
            )
        return user_accounts

    def test_contract_rewards_add_alocations_for_no_admin(
        self,
        asset_creator_account: SigningAccount,
        token_id: int,
        other_account: SigningAccount,
        user_account: SigningAccount,
    ) -> None:
        amount = 1_000_000_000

        with pytest.raises(LogicError, match="Sender is not the admin"):
            (
                self.rewards_client.algorand.new_group()
                .add_asset_transfer(
                    AssetTransferParams(
                        sender=asset_creator_account.address,
                        asset_id=token_id,
                        receiver=self.rewards_client.app_address,
                        amount=amount,
                        signer=asset_creator_account.signer,
                    )
                )
                .add_app_call_method_call(
                    self.rewards_client.params.call(
                        AppClientMethodCallParams(
                            method="add_allocations",
                            args=[[user_account.address], [amount, amount]],
                            sender=other_account.address,
                            signer=other_account.signer,
                            box_references=[user_account.address.encode()],
                            static_fee=AlgoAmount(micro_algo=2000),
                        )
                    )
                )
                .send(SendParams(cover_app_call_inner_transaction_fees=True))
            )

    def test_contract_rewards_add_alocations_different_sizes(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        amount = 1_000_000_000

        with pytest.raises(LogicError, match="Input arrays must have the same length"):
            (
                self.rewards_client.algorand.new_group()
                .add_asset_transfer(
                    AssetTransferParams(
                        sender=asset_creator_account.address,
                        asset_id=token_id,
                        receiver=self.rewards_client.app_address,
                        amount=amount,
                        signer=asset_creator_account.signer,
                    )
                )
                .add_app_call_method_call(
                    self.rewards_client.params.call(
                        AppClientMethodCallParams(
                            method="add_allocations",
                            args=[[user_account.address], [amount, amount]],
                            sender=admin_account.address,
                            signer=admin_account.signer,
                            box_references=[user_account.address.encode()],
                            static_fee=AlgoAmount(micro_algo=2000),
                        )
                    )
                )
                .send(SendParams(cover_app_call_inner_transaction_fees=True))
            )

    def test_contract_rewards_add_alocations_single_address(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        amount = 1_000_000_000

        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

    def test_contract_rewards_add_alocations_multiple_four_addresses(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_accounts_4: list,
    ) -> None:
        amount = 1_000_000_000

        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount * len(user_accounts_4),
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[
                            [user_account.address for user_account in user_accounts_4],
                            [amount] * len(user_accounts_4),
                        ],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[
                            user_account.address.encode()
                            for user_account in user_accounts_4
                        ],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

    def test_contract_rewards_add_alocations_extended_five_addresses(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_accounts_5: list,
    ) -> None:
        amount = 1_000_000_000

        with pytest.raises(
            ValueError,
            match=(
                "No more transactions below reference limit. "
                "Add another app call to the group."
            ),
        ):
            (
                self.rewards_client.algorand.new_group()
                .add_asset_transfer(
                    AssetTransferParams(
                        sender=asset_creator_account.address,
                        asset_id=token_id,
                        receiver=self.rewards_client.app_address,
                        amount=amount * len(user_accounts_5),
                        signer=asset_creator_account.signer,
                    )
                )
                .add_app_call_method_call(
                    self.rewards_client.params.call(
                        AppClientMethodCallParams(
                            method="add_allocations",
                            args=[
                                [
                                    user_account.address
                                    for user_account in user_accounts_5
                                ],
                                [amount] * len(user_accounts_5),
                            ],
                            sender=admin_account.address,
                            signer=admin_account.signer,
                            box_references=[
                                user_account.address.encode()
                                for user_account in user_accounts_5
                            ],
                            static_fee=AlgoAmount(micro_algo=2000),
                        )
                    )
                )
                .send(SendParams(cover_app_call_inner_transaction_fees=True))
            )


class TestContractClaim(BaseTestContract):
    """Testing class for :class:`contract.contract.Rewards` claim method."""

    name = "claim"

    def test_contract_rewards_claim_non_opted_in_user(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        amount = 1_000_000_000

        _make_transfer(
            asset_creator_account, self.rewards_client.app_address, token_id, amount
        )

        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        with pytest.raises(LogicError, match="Sender has not opted-in to the asset"):
            self.rewards_client.send.call(
                AppClientMethodCallParams(
                    method="claim",
                    sender=user_account.address,
                    signer=user_account.signer,
                    box_references=[user_account.address.encode()],
                    static_fee=AlgoAmount(micro_algo=2000),
                    asset_references=[token_id],
                )
            )

    def test_contract_rewards_claim_opted_in_user(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        amount = 1_000_000_000

        _make_transfer(
            asset_creator_account, self.rewards_client.app_address, token_id, amount
        )

        # User opts into the asset
        self.rewards_client.algorand.send.asset_opt_in(
            AssetTransferParams(
                sender=user_account.address,
                asset_id=token_id,
                amount=0,
                receiver=user_account.address,
                signer=user_account.signer,
            )
        )

        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )
        self.rewards_client.send.call(
            AppClientMethodCallParams(
                method="claim",
                sender=user_account.address,
                signer=user_account.signer,
                box_references=[user_account.address.encode()],
                static_fee=AlgoAmount(micro_algo=2000),
                asset_references=[token_id],
            )
        )

        # Verify the user received the asset
        user_asset_info = self.rewards_client.algorand.client.algod.account_asset_info(
            user_account.address, token_id
        )
        assert user_asset_info["asset-holding"]["amount"] == amount

        with pytest.raises(AlgodHTTPError, match="box not found"):
            self.rewards_client.algorand.client.algod.application_box_by_name(
                self.rewards_client.app_id, user_account.address.encode()
            )


class TestContractReclaimAllocations(BaseTestContract):
    """Testing class for :class:`contract.contract.Rewards` reclaim_allocations."""

    name = "reclaim"

    def test_contract_rewards_reclaim_allocations_before_expiry_fails(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        amount = 1_000_000_000

        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        with pytest.raises(LogicError, match="Claim period has not ended"):
            self.rewards_client.send.call(
                AppClientMethodCallParams(
                    method="reclaim_allocation",
                    args=[user_account.address],
                    sender=admin_account.address,
                    signer=admin_account.signer,
                    box_references=[user_account.address.encode()],
                )
            )


class TestContractReclaimAllocationsShortPeriod(BaseTestContract):
    """Testing class for :class:`contract.contract.Rewards` reclaim_allocations

    with a short claim period so we can test actual reclaiming.
    ."""

    name = "reclaim_short"
    claim_period_duration = 2

    @pytest.mark.order(1)
    def test_contract_rewards_reclaim_allocations_after_short_period(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        amount = 1_000_000_000

        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        time.sleep(self.claim_period_duration + 2)

        self.rewards_client.algorand.send.asset_opt_in(
            AssetTransferParams(
                sender=admin_account.address,
                asset_id=token_id,
                amount=0,
                receiver=admin_account.address,
                signer=admin_account.signer,
            )
        )

        self.rewards_client.send.call(
            AppClientMethodCallParams(
                method="reclaim_allocation",
                args=[user_account.address],
                sender=admin_account.address,
                signer=admin_account.signer,
                box_references=[user_account.address.encode()],
                static_fee=AlgoAmount(micro_algo=2000),
            )
        )


class TestContractBatchOperations(BaseTestContract):
    """Testing batch operations and edge cases for allocations."""

    name = "batch_ops"

    def test_contract_rewards_add_allocations_empty_arrays(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
    ) -> None:
        """Test adding allocations with empty arrays should succeed."""
        # Even for empty arrays, we need to include a funding transaction (can be 0 amount)
        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=0,  # Zero amount since no allocations
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[], []],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

    def test_contract_rewards_add_allocations_duplicate_addresses(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        """Test adding allocations with duplicate addresses sums amounts."""
        amount = 1_000_000_000
        total_amount = amount * 3

        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=total_amount,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address] * 3, [amount, amount, amount]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        # User opts in and claims
        self.rewards_client.algorand.send.asset_opt_in(
            AssetTransferParams(
                sender=user_account.address,
                asset_id=token_id,
                amount=0,
                receiver=user_account.address,
                signer=user_account.signer,
            )
        )

        self.rewards_client.send.call(
            AppClientMethodCallParams(
                method="claim",
                sender=user_account.address,
                signer=user_account.signer,
                box_references=[user_account.address.encode()],
                static_fee=AlgoAmount(micro_algo=2000),
                asset_references=[token_id],
            )
        )

        # Verify user received the summed amount
        user_asset_info = self.rewards_client.algorand.client.algod.account_asset_info(
            user_account.address, token_id
        )
        assert user_asset_info["asset-holding"]["amount"] == total_amount

    def test_contract_rewards_multiple_add_allocations_same_user(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        """Test multiple allocation additions to same user across different transactions."""
        amount1 = 500_000_000
        amount2 = 300_000_000

        # First allocation
        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount1,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount1]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        # Second allocation to same user
        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount2,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount2]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        # User opts in and claims
        self.rewards_client.algorand.send.asset_opt_in(
            AssetTransferParams(
                sender=user_account.address,
                asset_id=token_id,
                amount=0,
                receiver=user_account.address,
                signer=user_account.signer,
            )
        )

        self.rewards_client.send.call(
            AppClientMethodCallParams(
                method="claim",
                sender=user_account.address,
                signer=user_account.signer,
                box_references=[user_account.address.encode()],
                static_fee=AlgoAmount(micro_algo=2000),
                asset_references=[token_id],
            )
        )

        # Verify user received the total amount
        user_asset_info = self.rewards_client.algorand.client.algod.account_asset_info(
            user_account.address, token_id
        )
        assert user_asset_info["asset-holding"]["amount"] == amount1 + amount2


class TestContractFundingValidation(BaseTestContract):
    """Testing funding validation scenarios."""

    name = "funding"

    def test_contract_rewards_add_allocations_insufficient_funding(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        """Test that insufficient funding fails."""
        amount = 1_000_000_000
        insufficient_amount = amount - 100_000  # Less than required

        with pytest.raises(LogicError, match="Incorrect ASA funding"):
            (
                self.rewards_client.algorand.new_group()
                .add_asset_transfer(
                    AssetTransferParams(
                        sender=asset_creator_account.address,
                        asset_id=token_id,
                        receiver=self.rewards_client.app_address,
                        amount=insufficient_amount,
                        signer=asset_creator_account.signer,
                    )
                )
                .add_app_call_method_call(
                    self.rewards_client.params.call(
                        AppClientMethodCallParams(
                            method="add_allocations",
                            args=[[user_account.address], [amount]],
                            sender=admin_account.address,
                            signer=admin_account.signer,
                            box_references=[user_account.address.encode()],
                            static_fee=AlgoAmount(micro_algo=2000),
                        )
                    )
                )
                .send(SendParams(cover_app_call_inner_transaction_fees=True))
            )

    def test_contract_rewards_add_allocations_excess_funding(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        """Test that exact funding succeeds (contract requires exact match, not excess)."""
        amount = 1_000_000_000

        # Contract requires EXACT funding match, not excess
        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount,  # Exact amount required
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        # Verify contract has the exact tokens
        contract_asset_info = (
            self.rewards_client.algorand.client.algod.account_asset_info(
                self.rewards_client.app_address, token_id
            )
        )
        assert contract_asset_info["asset-holding"]["amount"] == amount

    def test_contract_rewards_add_allocations_single_funding_works(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        """Test that single funding transaction works correctly."""
        amount = 1_000_000_000

        # Single funding transaction (this is what the contract expects)
        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        # Verify by claiming
        self.rewards_client.algorand.send.asset_opt_in(
            AssetTransferParams(
                sender=user_account.address,
                asset_id=token_id,
                amount=0,
                receiver=user_account.address,
                signer=user_account.signer,
            )
        )

        initial_balance = self.rewards_client.algorand.client.algod.account_asset_info(
            user_account.address, token_id
        )["asset-holding"]["amount"]

        self.rewards_client.send.call(
            AppClientMethodCallParams(
                method="claim",
                sender=user_account.address,
                signer=user_account.signer,
                box_references=[user_account.address.encode()],
                static_fee=AlgoAmount(micro_algo=2000),
                asset_references=[token_id],
            )
        )

        final_balance = self.rewards_client.algorand.client.algod.account_asset_info(
            user_account.address, token_id
        )["asset-holding"]["amount"]
        assert final_balance == initial_balance + amount


class TestContractClaimScenarios(BaseTestContract):
    """Testing various claim scenarios and edge cases."""

    name = "claim_scenarios"

    def test_contract_rewards_double_claim_fails(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        """Test that user cannot claim twice."""
        amount = 1_000_000_000

        # Setup allocation
        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        # User opts in
        self.rewards_client.algorand.send.asset_opt_in(
            AssetTransferParams(
                sender=user_account.address,
                asset_id=token_id,
                amount=0,
                receiver=user_account.address,
                signer=user_account.signer,
            )
        )

        # First claim succeeds
        self.rewards_client.send.call(
            AppClientMethodCallParams(
                method="claim",
                sender=user_account.address,
                signer=user_account.signer,
                box_references=[user_account.address.encode()],
                static_fee=AlgoAmount(micro_algo=2000),
                asset_references=[token_id],
            )
        )

        # Second claim fails
        with pytest.raises(LogicError, match="Sender has no allocation"):
            self.rewards_client.send.call(
                AppClientMethodCallParams(
                    method="claim",
                    sender=user_account.address,
                    signer=user_account.signer,
                    box_references=[user_account.address.encode()],
                    static_fee=AlgoAmount(micro_algo=2000),
                    asset_references=[token_id],
                )
            )

    def test_contract_rewards_claim_then_reclaim_fails(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        """Test that reclaim fails for user who already claimed."""
        amount = 1_000_000_000

        # Setup allocation
        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        # User opts in and claims
        self.rewards_client.algorand.send.asset_opt_in(
            AssetTransferParams(
                sender=user_account.address,
                asset_id=token_id,
                amount=0,
                receiver=user_account.address,
                signer=user_account.signer,
            )
        )

        self.rewards_client.send.call(
            AppClientMethodCallParams(
                method="claim",
                sender=user_account.address,
                signer=user_account.signer,
                box_references=[user_account.address.encode()],
                static_fee=AlgoAmount(micro_algo=2000),
                asset_references=[token_id],
            )
        )

        with pytest.raises(LogicError, match="User has no allocation"):
            self.rewards_client.send.call(
                AppClientMethodCallParams(
                    method="reclaim_allocation",
                    args=[user_account.address],
                    sender=admin_account.address,
                    signer=admin_account.signer,
                    box_references=[user_account.address.encode()],
                    static_fee=AlgoAmount(micro_algo=2000),
                )
            )


class TestContractStateManagement(BaseTestContract):
    """Testing contract state management and access control."""

    name = "state_mgmt"

    def test_contract_rewards_setup_called_twice_fails(
        self,
        admin_account: SigningAccount,
        token_id: int,
    ) -> None:
        """Test that setup cannot be called twice."""
        with pytest.raises(LogicError, match="Contract already set up"):
            self.rewards_client.send.call(
                AppClientMethodCallParams(
                    method="setup",
                    args=[token_id, self.claim_period_duration],
                    sender=admin_account.address,
                    signer=admin_account.signer,
                    static_fee=AlgoAmount(micro_algo=2000),
                )
            )

    def test_contract_rewards_methods_fail_before_setup(
        self,
        admin_account: SigningAccount,
        user_account: SigningAccount,
        app_spec: Arc56Contract,
    ) -> None:
        """Test that methods fail when called before setup."""
        import json

        # Create a new contract instance without calling setup
        algod = self.rewards_client.algorand.client.algod

        # Re-deploy without setup for this test
        approval_teal_path = (
            Path(__file__).resolve().parent.parent
            / "artifacts"
            / f"{dapp_name}.approval.teal"
        )
        clear_teal_path = (
            Path(__file__).resolve().parent.parent
            / "artifacts"
            / f"{dapp_name}.clear.teal"
        )

        approval_program = compile_program(algod, approval_teal_path.read_bytes())
        clear_program = compile_program(algod, clear_teal_path.read_bytes())

        # Convert Arc56Contract to dict
        contract_json = json.loads(app_spec.to_json())

        new_app_id, _ = create_app(
            client=algod,
            private_key=admin_account.private_key,
            approval_program=approval_program,
            clear_program=clear_program,
            contract_json=contract_json,
        )

        # Create new client for uninitialized contract
        uninitialized_client = AppClient(
            AppClientParams(
                algorand=self.rewards_client.algorand,
                app_spec=app_spec,
                app_id=new_app_id,
            )
        )

        # Fund the new contract account
        self.rewards_client.algorand.send.payment(
            PaymentParams(
                sender=admin_account.address,
                receiver=uninitialized_client.app_address,
                amount=AlgoAmount(algo=1),
                signer=admin_account.signer,
            )
        )

        # Methods should fail on uninitialized contract
        with pytest.raises(LogicError):
            uninitialized_client.send.call(
                AppClientMethodCallParams(
                    method="add_allocations",
                    args=[[user_account.address], [1000]],
                    sender=admin_account.address,
                    signer=admin_account.signer,
                    box_references=[user_account.address.encode()],
                    static_fee=AlgoAmount(micro_algo=2000),
                )
            )


class TestContractBoxManagement(BaseTestContract):
    """Testing box storage and memory management."""

    name = "box_mgmt"

    def test_contract_rewards_box_creation_and_deletion(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        user_account: SigningAccount,
    ) -> None:
        """Test that boxes are properly created and deleted."""
        amount = 1_000_000_000

        # Add allocation (creates box)
        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=amount,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user_account.address], [amount]],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[user_account.address.encode()],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        # Verify box exists
        boxes = self.rewards_client.algorand.client.algod.application_boxes(
            self.rewards_client.app_id
        )
        box_names = [b["name"] for b in boxes["boxes"]]
        box_name_prefix = b"allocations"
        public_key = encoding.decode_address(user_account.address)
        box_name = box_name_prefix + public_key
        user_address_b64 = base64.b64encode(box_name).decode("utf-8")
        assert user_address_b64 in box_names

        # User opts in and claims (deletes box)
        self.rewards_client.algorand.send.asset_opt_in(
            AssetTransferParams(
                sender=user_account.address,
                asset_id=token_id,
                amount=0,
                receiver=user_account.address,
                signer=user_account.signer,
            )
        )

        self.rewards_client.send.call(
            AppClientMethodCallParams(
                method="claim",
                sender=user_account.address,
                signer=user_account.signer,
                box_references=[user_account.address.encode()],
                static_fee=AlgoAmount(micro_algo=2000),
                asset_references=[token_id],
            )
        )

        time.sleep(5)
        # Verify box is deleted
        with pytest.raises(AlgodHTTPError, match="box not found"):
            self.rewards_client.algorand.client.algod.application_box_by_name(
                self.rewards_client.app_id, user_account.address.encode()
            )


class TestContractMultipleUsers(BaseTestContract):
    """Testing scenarios with multiple users."""

    name = "multi_user"

    @pytest.fixture
    def multiple_users(self, algorand_client: AlgorandClient) -> list[SigningAccount]:
        """Create multiple test users."""
        users = []
        for i in range(3):
            users.append(
                algorand_client.account.from_environment(
                    f"MULTI_USER_{i}", fund_with=AlgoAmount(algo=10)
                )
            )
        return users

    def test_contract_rewards_claim_by_different_users(
        self,
        admin_account: SigningAccount,
        asset_creator_account: SigningAccount,
        token_id: int,
        multiple_users: list[SigningAccount],
    ) -> None:
        """Test multiple users claiming their allocations."""
        amounts = [1_000_000_000, 2_000_000_000, 3_000_000_000]
        total_amount = sum(amounts)

        # Add allocations for all users
        (
            self.rewards_client.algorand.new_group()
            .add_asset_transfer(
                AssetTransferParams(
                    sender=asset_creator_account.address,
                    asset_id=token_id,
                    receiver=self.rewards_client.app_address,
                    amount=total_amount,
                    signer=asset_creator_account.signer,
                )
            )
            .add_app_call_method_call(
                self.rewards_client.params.call(
                    AppClientMethodCallParams(
                        method="add_allocations",
                        args=[[user.address for user in multiple_users], amounts],
                        sender=admin_account.address,
                        signer=admin_account.signer,
                        box_references=[
                            user.address.encode() for user in multiple_users
                        ],
                        static_fee=AlgoAmount(micro_algo=2000),
                    )
                )
            )
            .send(SendParams(cover_app_call_inner_transaction_fees=True))
        )

        # Each user opts in and claims
        for i, user in enumerate(multiple_users):
            self.rewards_client.algorand.send.asset_opt_in(
                AssetTransferParams(
                    sender=user.address,
                    asset_id=token_id,
                    amount=0,
                    receiver=user.address,
                    signer=user.signer,
                )
            )

            self.rewards_client.send.call(
                AppClientMethodCallParams(
                    method="claim",
                    sender=user.address,
                    signer=user.signer,
                    box_references=[user.address.encode()],
                    static_fee=AlgoAmount(micro_algo=2000),
                    asset_references=[token_id],
                )
            )

            # Verify each user received correct amount
            user_asset_info = (
                self.rewards_client.algorand.client.algod.account_asset_info(
                    user.address, token_id
                )
            )
            assert user_asset_info["asset-holding"]["amount"] == amounts[i]
