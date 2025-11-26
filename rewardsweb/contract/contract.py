"""Rewards Suite smart contract module."""

from algopy import (
    Account,
    Asset,
    BoxMap,
    Global,
    GlobalState,
    Struct,
    TransactionType,
    Txn,
    UInt64,
    arc4,
    itxn,
    op,
    urange,
)


class Allocation(Struct):
    """Represents a user's allocation with amount and expiration."""

    amount: UInt64
    expires_at: UInt64


class Rewards(arc4.ARC4Contract):
    """
    A rewards smart contract for distributing an ASA (Algorand Standard Asset).

    The contract is managed by an admin who can:
    1. Fund the contract with the ASA.
    2. Register user addresses with specific amounts to be claimed.

    Users can:
    1. Claim their allocated amount of the ASA.

    The admin can also reclaim any remaining funds after a specified claim period ends.
    """

    def __init__(self) -> None:
        """
        Initializes the contract's state variables.
        """

        # The administrative address for the contract
        self.admin_address = GlobalState(Account)

        # The ID of the ASA being distributed
        self.token_id = GlobalState(UInt64)

        # The duration of the claim period in seconds
        self.claim_period_duration = GlobalState(UInt64)

        # A BoxMap to store the allocation details for each user address.
        # Key: User's Address, Value: Allocation struct
        self.allocations = BoxMap(Account, Allocation)

    @arc4.baremethod(allow_actions=["NoOp"], create="require")
    def create_application(self) -> None:
        """
        Handles the application creation.
        This method is called only once, when the contract is deployed.
        It sets the sender of the creation transaction as the admin.
        """
        self.admin_address.value = Txn.sender
        self.token_id.value = UInt64(0)
        self.claim_period_duration.value = UInt64(0)

    @arc4.baremethod(allow_actions=["DeleteApplication"])
    def delete_application(self) -> None:
        """
        Allows the admin to delete the application.
        """
        assert Txn.sender == self.admin_address.value, "Sender is not the admin"

    @arc4.abimethod
    def setup(self, token: Asset, claim_period_duration: UInt64) -> None:
        """
        Sets up the contract with the token ID and the claim period duration.
        This method can only be called by the admin and only once.
        It also makes the contract account opt-in to the specified ASA.

        Args:
            token: The ASA to be distributed.
            claim_period_duration: The duration of the claim period in seconds.
        """

        assert Txn.sender == self.admin_address.value, "Sender is not the admin"
        assert self.token_id.value == 0, "Contract already set up"
        self.token_id.value = token.id
        self.claim_period_duration.value = claim_period_duration

        # Contract opts-in to the ASA
        itxn.AssetTransfer(
            xfer_asset=self.token_id.value,
            asset_receiver=Global.current_application_address,
            asset_amount=0,
        ).submit()

    @arc4.abimethod
    def add_allocations(
        self,
        addresses: arc4.DynamicArray[arc4.Address],
        amounts: arc4.DynamicArray[arc4.UInt64],
    ) -> None:
        """
        Adds or updates allocations for a batch of users.
        If a user already has an allocation, the new amount is added to the existing one,
        and the expiration is reset.

        Args:
            addresses: An array of user addresses.
            amounts: An array of corresponding allocation amounts.
        """

        assert Txn.sender == self.admin_address.value, "Sender is not the admin"
        assert (
            addresses.length == amounts.length
        ), "Input arrays must have the same length"

        required_funding = UInt64(0)
        for j in urange(addresses.length):
            required_funding += amounts[j].as_uint64()

        assert op.Global.group_size >= UInt64(2), "Missing funding transaction in group"

        funded_amount = UInt64(0)
        for i in urange(op.Global.group_size):
            if op.GTxn.type_enum(i) == TransactionType.AssetTransfer:
                if op.GTxn.xfer_asset(i).id == self.token_id.value:
                    if op.GTxn.asset_receiver(i) == Global.current_application_address:
                        funded_amount += op.GTxn.asset_amount(i)

        assert funded_amount == required_funding, "Incorrect ASA funding"

        expires_at = Global.latest_timestamp + self.claim_period_duration.value
        for i in urange(addresses.length):
            address = addresses[i].native
            amount = amounts[i].as_uint64()
            allocation_box = self.allocations.box(address)
            if allocation_box:
                # Update existing allocation
                existing_allocation = allocation_box.value.copy()
                existing_allocation.amount += amount
                existing_allocation.expires_at = expires_at
                allocation_box.value = existing_allocation.copy()

            else:
                # Create new allocation
                assert allocation_box.create()
                allocation_box.value = Allocation(amount=amount, expires_at=expires_at)

    @arc4.abimethod(name="claim")
    def claim(self) -> None:
        """
        Allows a user to claim their allocated tokens.
        The user must opt-in to the ASA in a separate transaction within the same atomic group
        as the call to this method.
        The contract then transfers the allocated ASA amount to the user and
        removes their allocation to prevent re-claiming.
        """
        sender = Txn.sender
        allocation_box = self.allocations.box(sender)
        assert allocation_box, "Sender has no allocation"

        allocation = allocation_box.value.copy()
        assert (
            Global.latest_timestamp <= allocation.expires_at
        ), "Claim period has ended"

        amount_to_claim = allocation.amount

        # Check if the user is already opted-in to the asset
        balance, opted_in = op.AssetHoldingGet.asset_balance(
            sender, self.token_id.value
        )
        assert opted_in, "Sender has not opted-in to the asset"

        # Create the transaction to transfer the allocated amount
        itxn.AssetTransfer(
            xfer_asset=self.token_id.value,
            asset_receiver=sender,
            asset_amount=amount_to_claim,
        ).submit()

        # Delete the allocation to prevent claiming again
        del allocation_box.value

    @arc4.abimethod
    def reclaim_allocation(self, user_address: Account) -> None:
        """
        Allows the admin to reclaim a user's allocation if it has expired.

        Args:
            user_address: The address of the user whose allocation is to be reclaimed.
        """
        assert Txn.sender == self.admin_address.value, "Sender is not the admin"
        allocation_box = self.allocations.box(user_address)
        assert allocation_box, "User has no allocation"
        allocation = allocation_box.value.copy()
        assert (
            Global.latest_timestamp > allocation.expires_at
        ), "Claim period has not ended for this user"

        # Transfer the user's allocated amount back to the admin
        itxn.AssetTransfer(
            xfer_asset=self.token_id.value,
            asset_receiver=self.admin_address.value,
            asset_amount=allocation.amount,
        ).submit()

        # Delete the allocation
        del allocation_box.value
