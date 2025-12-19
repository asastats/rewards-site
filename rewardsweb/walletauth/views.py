"""Module containing views for wallet authorization and authentication."""

import base64
import json
from secrets import token_hex

import msgpack
from algosdk.encoding import is_valid_address
from algosdk.transaction import SignedTransaction
from django.conf import settings
from django.contrib.auth import get_user_model, login
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from contract.network import reclaimable_addresses
from core.models import Contribution, Contributor, Profile
from rewards.helpers import (
    added_allocations_for_addresses,
    claim_successful_for_address,
    reclaimed_allocation_for_address,
)
from utils.constants.core import (
    ALGORAND_WALLETS,
    WALLET_CONNECT_NETWORK_OPTIONS,
    WALLET_CONNECT_NONCE_PREFIX,
)
from utils.helpers import verify_signed_transaction
from walletauth.models import WalletNonce

User = get_user_model()


class WalletsAPIView(APIView):
    """Retrieve a list of supported wallets.

    :param request: HTTP request object
    :return: JSON response containing supported wallets
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request to return supported wallets.

        :param request: HTTP request object
        :return: JSON list of supported wallets, each containing:
            - id (str): wallet identifier
            - name (str): user-friendly wallet name
        """
        wallets = ALGORAND_WALLETS
        return Response(wallets)


class ActiveNetworkAPIView(APIView):
    """Get or update the active network stored in the session.

    - `GET` returns the currently active network (default: `testnet`)
    - `POST` sets a new active network

    :param request: HTTP request object
    :return: JSON response with network information or error
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request to retrieve the active network.

        :param request: HTTP request object
        :return: JSON response with:
            - network (str): current active network name
        """
        active_network = request.session.get("active_network", "testnet")
        return Response({"network": active_network})

    def post(self, request, *args, **kwargs):
        """Handle POST request to set the active network.

        Expects JSON with:
            - network (str): network to set (must be in `WALLET_CONNECT_NETWORK_OPTIONS`)

        :param request: HTTP request object
        :return: JSON response with:
            - success (bool): True if network was updated
            - network (str): network that was set
            OR
            - error (str): message if invalid input provided
        """
        try:
            # DRF Request gives request.data. Django Request gives request.body.
            data = getattr(request, "data", None)
            if data is None:
                data = json.loads(request.body)

            network = data.get("network")

        except Exception:
            return Response({"error": "Invalid JSON"}, status=400)

        if network not in WALLET_CONNECT_NETWORK_OPTIONS:
            return Response({"error": "Invalid network"}, status=400)

        request.session["active_network"] = network
        return Response({"success": True, "network": network})


class WalletNonceAPIView(APIView):
    """Generate nonce for wallet authentication."""

    def post(self, request, *args, **kwargs):
        """Create nonce linked to address.

        Expected JSON:
            - address (str)

        :param request: HTTP request object
        :return: JSON response with:
            - nonce (str)
            - prefix (str)
        """

        try:
            data = getattr(request, "data", None)
            if data is None:
                data = json.loads(request.body.decode())

            address = data.get("address")

        except Exception:
            return Response({"error": "Invalid JSON"}, status=400)

        if not address or not is_valid_address(address):
            return Response(
                {"error": f"Invalid or missing address: {address}"}, status=400
            )

        nonce = token_hex(16)
        WalletNonce.objects.create(address=address, nonce=nonce)

        return Response({"nonce": nonce, "prefix": WALLET_CONNECT_NONCE_PREFIX})


class WalletVerifyAPIView(APIView):
    """Verify wallet signature and log the user in."""

    def post(self, request, *args, **kwargs):
        """Verify signed transaction and authenticate the user.

        Expected JSON:
            - address (str)
            - signedTransaction (str)
            - nonce (str)

        :return: JSON { "success": bool, "redirect_url": "/" } on success
        """
        try:
            address = request.data.get("address")
            signed_transaction_base64 = request.data.get("signedTransaction")
            nonce_str = request.data.get("nonce")
        except Exception:
            return Response({"success": False, "error": "Invalid request"}, status=400)

        if not address or not signed_transaction_base64 or not nonce_str:
            return Response({"success": False, "error": "Missing data"}, status=400)

        if not is_valid_address(address):
            return Response(
                {"success": False, "error": f"Invalid address: {address}"}, status=400
            )

        try:
            nonce_obj = WalletNonce.objects.get(
                nonce=nonce_str, address=address, used=False
            )
        except WalletNonce.DoesNotExist:
            print(f"[WalletVerifyAPIView] Nonce not found or already used: {nonce_str}")
            return Response(
                {"success": False, "error": "Nonce not found or already used"},
                status=400,
            )

        if nonce_obj.is_expired():
            print(f"[WalletVerifyAPIView] Nonce expired: {nonce_str}")
            return Response({"success": False, "error": "Nonce expired"}, status=400)

        # Decode and verify the signed transaction
        try:
            signed_tx_bytes = base64.b64decode(signed_transaction_base64)
            # Decode msgpack to dict
            txn_dict = msgpack.unpackb(signed_tx_bytes)
            # Undictify to SignedTransaction
            stxn = SignedTransaction.undictify(txn_dict)
            note = (
                stxn.transaction.note.decode("utf-8")
                if stxn.transaction.note
                else "No note"
            )
            print(
                f"[WalletVerifyAPIView] Decoded signed transaction, sender: "
                f"{stxn.transaction.sender}, note: {note}"
            )

            # Verify the signature
            verified = verify_signed_transaction(stxn)
            if not verified:
                print(
                    f"[WalletVerifyAPIView] Signature verification failed "
                    f"for address: {address}"
                )
                return Response(
                    {"success": False, "error": "Invalid signature"}, status=400
                )

            # Check if the note contains the nonce
            note_str = (
                stxn.transaction.note.decode("utf-8") if stxn.transaction.note else ""
            )
            if (
                not note_str.startswith(WALLET_CONNECT_NONCE_PREFIX)
                or note_str.split(WALLET_CONNECT_NONCE_PREFIX)[1] != nonce_str
            ):
                print(
                    f"[WalletVerifyAPIView] Note mismatch - "
                    f"expected nonce: {nonce_str}, got note: {note_str}"
                )
                return Response(
                    {"success": False, "error": "Invalid nonce in transaction"},
                    status=400,
                )

            print(
                f"[WalletVerifyAPIView] Signature and nonce "
                f"verified for address: {address}"
            )

        except Exception as e:
            print(f"[WalletVerifyAPIView] Verification error: {e}")
            return Response(
                {"success": False, "error": "Invalid signed transaction"}, status=400
            )

        nonce_obj.mark_used()
        print(f"[WalletVerifyAPIView] Nonce marked used: {nonce_str}")

        # Link or create user via Contributor
        contributor = Contributor.objects.filter(address=address).first()
        if contributor:
            profile = Profile.objects.filter(contributor=contributor).first()
            if profile:
                user = profile.user
            else:
                user = User.objects.create(username=f"{address[:5]}..{address[-5:]}")
                user.profile.contributor = contributor
                user.profile.save()
        else:
            user = User.objects.create(username=f"{address[:5]}..{address[-5:]}")
            contributor = Contributor.objects.create(
                name=user.username, address=address
            )
            user.profile.contributor = contributor
            user.profile.save()

        print(f"[WalletVerifyAPIView] Logged in user: {user.username}")

        # Set the backend and log in the user
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)

        redirect_url = request.data.get("next", settings.LOGIN_REDIRECT_URL)

        return Response({"success": True, "redirect_url": redirect_url})


class AddAllocationsAPIView(APIView):
    """Provide data for adding new allocations."""

    def post(self, request, *args, **kwargs):
        """Return allocation data for the received address.

        Expected JSON:
            - address (str): Algorand wallet address

        :param request: HTTP request object
        :return: JSON response with:
            - addresses (list[str])
            - amounts (list[int])
            OR error message
        """
        try:
            data = getattr(request, "data", None)
            if data is None:
                data = json.loads(request.body.decode())

            address = data.get("address")

        except Exception:
            return Response({"error": "Invalid JSON"}, status=400)

        if not address or not is_valid_address(address):
            return Response(
                {"error": f"Invalid or missing address: {address}"}, status=400
            )

        addresses, amounts = (
            Contribution.objects.addressed_contributions_addresses_and_amounts()
        )
        allocations = {"addresses": addresses, "amounts": amounts}
        return Response(allocations)


class AllocationsSuccessfulAPIView(APIView):
    """Mark allocations as successful."""

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        """Update status of related issues to PROCESSED.

        Expected JSON:
            - addresses (list[str])
            - txIDs (list[str])

        :param request: HTTP request object
        :return: JSON response with:
            - success (bool)
            OR error message
        """
        try:
            data = getattr(request, "data", None)
            if data is None:
                data = json.loads(request.body.decode())

            addresses = data.get("addresses")
            txid = data.get("txIDs")

        except Exception:
            return Response({"error": "Invalid JSON"}, status=400)

        if not addresses:
            return Response({"error": "Missing addresses"}, status=400)

        added_allocations_for_addresses(request, addresses, txid)

        return Response({"success": True})


class ClaimSuccessfulAPIView(APIView):
    """Mark all user's contributions as claimed."""

    def post(self, request, *args, **kwargs):
        """Update status of related issues to ARCHIVED.

        Expected JSON:
            - address (str)
            - txIDs (str)

        :param request: HTTP request object
        :return: JSON response with:
            - success (bool)
            OR error message
        """
        try:
            data = getattr(request, "data", None)
            if data is None:
                data = json.loads(request.body.decode())

            address = data.get("address")
            txid = data.get("txID")

        except Exception:
            return Response({"error": "Invalid JSON"}, status=400)

        if not address or not is_valid_address(address):
            return Response(
                {"error": f"Invalid or missing address: {address}"}, status=400
            )

        claim_successful_for_address(request, address, txid)

        return Response({"success": True})


class ReclaimAllocationsAPIView(APIView):
    """Provide a list of allocations that can be reclaimed."""

    def post(self, request, *args, **kwargs):
        """Return reclaimable allocation data.

        Expected JSON:
            - address (str)

        :param request: HTTP request object
        :return: JSON response with reclaimable allocation data
        """
        try:
            data = getattr(request, "data", None)
            if data is None:
                data = json.loads(request.body.decode())

            address = data.get("address")

        except Exception:
            return Response({"error": "Invalid JSON"}, status=400)

        if not address or not is_valid_address(address):
            return Response(
                {"error": f"Invalid or missing address: {address}"}, status=400
            )

        reclaimable_allocations = {"addresses": reclaimable_addresses()}
        return Response(reclaimable_allocations)


class ReclaimSuccessfulAPIView(APIView):
    """Mark reclaim allocation as successful."""

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        """Update status of related issues to PROCESSED.

        Expected JSON:
            - address (str)
            - txID (str)

        :param request: HTTP request object
        :return: JSON response with:
            - success (bool)
            OR error message
        """
        try:
            data = getattr(request, "data", None)
            if data is None:
                data = json.loads(request.body.decode())

            address = data.get("address")
            txid = data.get("txID")

        except Exception:
            return Response({"error": "Invalid JSON"}, status=400)

        if not address:
            return Response({"error": "Missing address"}, status=400)

        reclaimed_allocation_for_address(request, address, txid)

        return Response({"success": True})
