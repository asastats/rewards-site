"""Testing module for rewards app's views."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages import get_messages
from django.test import RequestFactory
from django.urls import reverse

from core.models import Contributor
from rewards.views import AddAllocationsView, ClaimView, ReclaimAllocationsView

User = get_user_model()


class TestRewardsClaimViews:
    """Test suite for :class:`rewards.views.ClaimView`."""

    @pytest.fixture
    def rf(self):
        return RequestFactory()

    @pytest.fixture
    def user(self, db):
        """Create a normal authenticated user."""
        return User.objects.create_user(username="testuser", password="pass123")

    @pytest.mark.django_db
    def test_claimview_requires_login(self, rf):
        request = rf.get(reverse("claim"))
        request.user = AnonymousUser()
        response = ClaimView.as_view()(request)
        # Redirects to login page
        assert response.status_code == 302
        assert "/login" in response.url.lower()

    # # get_context_data
    @pytest.mark.django_db
    def test_claimview_context_amount_functionality(self, rf, user, mocker):
        amount = 1000
        mocked_fetch = mocker.patch(
            "rewards.views.claimable_amount_for_address", return_value=amount
        )
        request = rf.get(reverse("claim"))
        request.user = user
        contributor = Contributor("contributor")
        address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
        contributor.address = address
        user.profile.contributor = contributor
        response = ClaimView.as_view()(request)
        context = response.context_data
        assert context["amount"] == amount
        mocked_fetch.assert_called_once_with(address)

    @pytest.mark.django_db
    def test_claimview_context_amount_false_no_contributor(self, rf, user, mocker):
        mocked_fetch = mocker.patch("rewards.views.claimable_amount_for_address")
        request = rf.get(reverse("claim"))
        request.user = user
        user.profile.contributor = None
        response = ClaimView.as_view()(request)
        context = response.context_data
        assert context["amount"] == 0
        mocked_fetch.assert_not_called()

    @pytest.mark.django_db
    def test_claimview_context_amount_false_no_contributor_address(
        self, rf, user, mocker
    ):
        mocked_fetch = mocker.patch("rewards.views.claimable_amount_for_address")
        request = rf.get(reverse("claim"))
        request.user = user
        contributor = Contributor("contributor")
        user.profile.contributor = contributor
        response = ClaimView.as_view()(request)
        context = response.context_data
        assert context["amount"] == 0
        mocked_fetch.assert_not_called()

    @pytest.mark.django_db
    def test_claimview_context_amount_false_no_valid_contributor_address(
        self, rf, user, mocker
    ):
        mocked_fetch = mocker.patch("rewards.views.claimable_amount_for_address")
        request = rf.get(reverse("claim"))
        request.user = user
        contributor = Contributor("contributor")
        contributor.address = "ADDRESS"
        user.profile.contributor = contributor
        response = ClaimView.as_view()(request)
        context = response.context_data
        assert context["amount"] == 0
        mocked_fetch.assert_not_called()

    @pytest.mark.django_db
    def test_claimview_context_amount_0_for_valid_contributor_address(
        self, rf, user, mocker
    ):
        mocked_fetch = mocker.patch(
            "rewards.views.claimable_amount_for_address", return_value=0
        )
        request = rf.get(reverse("claim"))
        request.user = user
        contributor = Contributor("contributor")
        address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
        contributor.address = address
        user.profile.contributor = contributor
        response = ClaimView.as_view()(request)
        context = response.context_data
        assert context["amount"] == 0
        mocked_fetch.assert_called_once_with(address)

    @pytest.mark.django_db
    def test_claimview_context_amount_0_for_valueerror(self, rf, user, mocker):
        mocked_fetch = mocker.patch(
            "rewards.views.claimable_amount_for_address", side_effect=ValueError("")
        )
        request = rf.get(reverse("claim"))
        request.user = user
        contributor = Contributor("contributor")
        address = "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
        contributor.address = address
        user.profile.contributor = contributor
        response = ClaimView.as_view()(request)
        context = response.context_data
        assert context["amount"] == 0
        mocked_fetch.assert_called_once_with(address)


class TestRewardsAddAllocationsView:
    """Test suite for :class:`rewards.views.AddAllocationsView`."""

    @pytest.fixture
    def rf(self):
        return RequestFactory()

    @pytest.fixture
    def user(self, db):
        """Create a normal authenticated user."""
        return User.objects.create_user(username="testuser", password="pass123")

    @pytest.fixture
    def superuser(self, db):
        """Create a superuser."""
        return User.objects.create_superuser(username="admin", password="pass123")

    @pytest.mark.django_db
    def test_addallocationsview_requires_login(self, rf, mocker):
        """Ensure the view redirects anonymous users to login page."""
        mocker.patch("rewards.views.is_admin_account_configured")
        mocker.patch(
            (
                "rewards.views.Contribution.objects."
                "addressed_contributions_addresses_and_amounts"
            ),
            return_value=(["ADDR1", "ADDR2"], [10, 20]),
        )
        request = rf.get(reverse("add_allocations"))
        request.user = AnonymousUser()
        response = AddAllocationsView.as_view()(request)
        assert response.status_code == 302  # redirect
        assert "/login" in response.url.lower()

    @pytest.mark.django_db
    def test_addallocationsview_superuser_can_access(self, rf, superuser, mocker):
        """Superusers should be able to access the page."""
        mocker.patch("rewards.views.is_admin_account_configured")
        mocker.patch(
            (
                "rewards.views.Contribution.objects."
                "addressed_contributions_addresses_and_amounts"
            ),
            return_value=(["ADDR1", "ADDR2"], [10, 20]),
        )
        request = rf.get(reverse("add_allocations"))
        request.user = superuser
        response = AddAllocationsView.as_view()(request)
        assert response.status_code == 200
        assert response.template_name == ["rewards/add_allocations.html"]

    # # get_context_data
    @pytest.mark.django_db
    def test_addallocationsview_context_contains_allocations(
        self, rf, superuser, mocker
    ):
        """Ensure allocations from queryset are added to context."""
        # Mock database call
        mocked_contribs = mocker.patch(
            (
                "rewards.views.Contribution.objects."
                "addressed_contributions_addresses_and_amounts"
            ),
            return_value=(["ADDR1", "ADDR2"], [10, 20]),
        )
        mocker.patch("rewards.views.is_admin_account_configured")
        request = rf.get(reverse("add_allocations"))
        request.user = superuser
        response = AddAllocationsView.as_view()(request)
        context = response.context_data
        assert list(context["allocations"]) == [("ADDR1", 10), ("ADDR2", 20)]
        # Ensures function was called exactly once
        mocked_contribs.assert_called_once_with()

    @pytest.mark.django_db
    def test_addallocationsview_context_contains_use_admin_account(
        self, rf, superuser, mocker
    ):
        """Ensure allocations from queryset are added to context."""
        mocker.patch(
            (
                "rewards.views.Contribution.objects."
                "addressed_contributions_addresses_and_amounts"
            ),
            return_value=(["ADDR1", "ADDR2"], [10, 20]),
        )
        mocked_admin = mocker.patch("rewards.views.is_admin_account_configured")
        request = rf.get(reverse("add_allocations"))
        request.user = superuser
        response = AddAllocationsView.as_view()(request)
        context = response.context_data
        assert context["use_admin_account"] == mocked_admin.return_value
        # Ensures function was called exactly once
        mocked_admin.assert_called_once_with()

    @pytest.mark.django_db
    def test_addallocationsview_context_for_no_allocations(self, rf, superuser, mocker):
        """Ensure allocations from queryset are added to context."""
        # Mock database call
        mocker.patch(
            (
                "rewards.views.Contribution.objects."
                "addressed_contributions_addresses_and_amounts"
            ),
            return_value=([], []),
        )
        mocker.patch("rewards.views.is_admin_account_configured")
        request = rf.get(reverse("add_allocations"))
        request.user = superuser
        response = AddAllocationsView.as_view()(request)
        context = response.context_data
        assert "allocations" not in context
        assert "use_admin_account" not in context

    # # post
    @pytest.mark.django_db
    def test_addallocationsview_normal_user_blocked(self, rf, user):
        """Non-superusers should NOT be allowed to access the page."""
        request = rf.get(reverse("add_allocations"))
        request.user = user
        response = AddAllocationsView.as_view()(request)
        # LoginRequiredMixin lets login first, so user gets 302 to login
        assert response.status_code in (302, 403)

    @pytest.mark.django_db
    def test_addallocationsview_post_admin_account_not_configured(
        self, client, superuser, mocker
    ):
        """Test post when admin account is not configured."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=False)
        client.force_login(superuser)
        response = client.post(reverse("add_allocations"))
        assert response.status_code == 204  # Changed from 302 to 204
        assert response["HX-Redirect"] == reverse("add_allocations")
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        assert any(
            "Admin account not configured" in str(message) for message in messages
        )

    @pytest.mark.django_db
    def test_addallocationsview_post_single_batch_success(
        self, client, superuser, mocker
    ):
        """Test successful post with single batch processing."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        # Mock contributions and allocation processing
        mock_contributions = mocker.MagicMock()
        mocker.patch(
            "rewards.views.Contribution.objects.filter", return_value=mock_contributions
        )
        # Mock the generator to return one successful batch
        mock_generator = mocker.patch(
            "rewards.views.process_allocations_for_contributions"
        )
        mock_generator.return_value = [("tx_hash_123", ["address1", "address2"])]
        # Mock the update method
        mock_update = mocker.patch(
            "rewards.views.Contribution.objects.update_issue_statuses_for_addresses"
        )
        # Mock user profile logging
        mock_profile = mocker.MagicMock()
        mocker.patch.object(User, "profile", mock_profile)
        client.force_login(superuser)
        response = client.post(reverse("add_allocations"))
        assert response.status_code == 204
        assert response["HX-Redirect"] == reverse("add_allocations")
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        message_texts = [str(msg) for msg in messages]
        assert any(
            "✅ Allocation successful TXID: tx_hash_123" in msg for msg in message_texts
        )
        assert any("✅ All batches completed" in msg for msg in message_texts)
        # Verify update was called
        mock_update.assert_called_once_with(
            ["address1", "address2"], mock_contributions
        )
        # Verify log action was called with formatted addresses
        mock_profile.log_action.assert_called_once_with(
            "boxes_created", "tx_hash_123; addre..ress1; addre..ress2"
        )

    @pytest.mark.django_db
    def test_addallocationsview_post_multiple_batches_mixed_results(
        self, client, superuser, mocker
    ):
        """Test post with multiple batches including both success and failure."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        mock_contributions = mocker.MagicMock()
        mocker.patch(
            "rewards.views.Contribution.objects.filter", return_value=mock_contributions
        )
        # Mock generator with mixed results
        mock_generator = mocker.patch(
            "rewards.views.process_allocations_for_contributions"
        )
        mock_generator.return_value = [
            ("tx_hash_1", ["addr1", "addr2"]),  # Batch 1 success
            (False, ["error text"]),  # Batch 2 failures
        ]
        mock_update = mocker.patch(
            "rewards.views.Contribution.objects.update_issue_statuses_for_addresses"
        )
        mock_profile = mocker.MagicMock()
        mocker.patch.object(User, "profile", mock_profile)
        client.force_login(superuser)
        response = client.post(reverse("add_allocations"))
        assert response.status_code == 204
        # Check messages for mixed results
        messages = list(get_messages(response.wsgi_request))
        message_texts = [str(msg) for msg in messages]
        assert any(
            "✅ Allocation successful TXID: tx_hash_1" in msg for msg in message_texts
        )
        assert any("❌ error text" in msg for msg in message_texts)
        assert not any("✅ All batches completed" in msg for msg in message_texts)
        mock_update.assert_called_once_with(["addr1", "addr2"], mock_contributions)
        assert mock_profile.log_action.call_count == 1

    @pytest.mark.django_db
    def test_addallocationsview_post_first_batch_fails(self, client, superuser, mocker):
        """Test post when all batches fail."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        mock_contributions = mocker.MagicMock()
        mocker.patch(
            "rewards.views.Contribution.objects.filter", return_value=mock_contributions
        )
        # Mock generator with all failures
        mock_generator = mocker.patch(
            "rewards.views.process_allocations_for_contributions"
        )
        mock_generator.return_value = [(False, ["error text"])]
        mock_update = mocker.patch(
            "rewards.views.Contribution.objects.update_issue_statuses_for_addresses"
        )
        mock_profile = mocker.MagicMock()
        mocker.patch.object(User, "profile", mock_profile)
        client.force_login(superuser)
        response = client.post(reverse("add_allocations"))
        assert response.status_code == 204
        # Check error messages
        messages = list(get_messages(response.wsgi_request))
        message_texts = [str(msg) for msg in messages]
        error_count = sum(1 for msg in message_texts if "❌ error text" in msg)
        assert error_count == 1
        assert not any("✅ All batches completed" in msg for msg in message_texts)
        # Verify no updates were made
        mock_update.assert_not_called()
        mock_profile.log_action.assert_not_called()

    @pytest.mark.django_db
    def test_addallocationsview_post_no_contributions(self, client, superuser, mocker):
        """Test post when there are no contributions to process."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        # Mock empty contributions
        mock_contributions = mocker.MagicMock()
        mocker.patch(
            "rewards.views.Contribution.objects.filter", return_value=mock_contributions
        )
        # Mock generator with no batches (empty case)
        mock_generator = mocker.patch(
            "rewards.views.process_allocations_for_contributions"
        )
        mock_generator.return_value = []  # No batches yielded
        mock_update = mocker.patch(
            "rewards.views.Contribution.objects.update_issue_statuses_for_addresses"
        )
        client.force_login(superuser)
        response = client.post(reverse("add_allocations"))
        assert response.status_code == 204
        # Check only completion message
        messages = list(get_messages(response.wsgi_request))
        message_texts = [str(msg) for msg in messages]
        assert any("✅ All batches completed" in msg for msg in message_texts)
        assert not any("❌ Allocation batch failed" in msg for msg in message_texts)
        assert not any("✅ Allocation successful TXID:" in msg for msg in message_texts)
        # Verify no updates were made
        mock_update.assert_not_called()

    @pytest.mark.django_db
    def test_addallocationsview_post_normal_user_blocked(self, client, user, mocker):
        """Test that normal users cannot access post method."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        client.force_login(user)
        response = client.post(reverse("add_allocations"))
        # Should be redirected or forbidden
        assert response.status_code in (302, 403)

    @pytest.mark.django_db
    def test_addallocationsview_post_anonymous_user_blocked(self, client, mocker):
        """Test that anonymous users cannot access post method."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        response = client.post(reverse("add_allocations"))
        # Should be redirected to login
        assert response.status_code == 302
        assert "/login" in response.url


class TestRewardsReclaimAllocationsView:
    """Test suite for :class:`rewards.views.ReclaimAllocationsView`."""

    @pytest.fixture
    def rf(self):
        return RequestFactory()

    @pytest.fixture
    def user(self, db):
        """Create a normal authenticated user."""
        return User.objects.create_user(username="testuser", password="pass123")

    @pytest.fixture
    def superuser(self, db):
        """Create a superuser."""
        return User.objects.create_superuser(username="admin", password="pass123")

    @pytest.mark.django_db
    def test_reclaimallocationsview_requires_login(self, rf):
        request = rf.get(reverse("reclaim_allocations"))
        request.user = AnonymousUser()
        response = ReclaimAllocationsView.as_view()(request)
        assert response.status_code == 302
        assert "/login" in response.url.lower()

    @pytest.mark.django_db
    def test_reclaimallocationsview_superuser_can_access(self, rf, superuser, mocker):
        mocker.patch("rewards.views.is_admin_account_configured")
        mocker.patch("rewards.views.reclaimable_addresses")
        request = rf.get(reverse("reclaim_allocations"))
        request.user = superuser
        response = ReclaimAllocationsView.as_view()(request)
        assert response.status_code == 200
        assert response.template_name == ["rewards/reclaim_allocations.html"]

    # # get_context_data
    @pytest.mark.django_db
    def test_reclaimallocationsview_context_contains_addresses(
        self, rf, superuser, mocker
    ):
        """Ensure addresses are added to context."""
        # Mock database call
        mocker.patch("rewards.views.is_admin_account_configured")
        mocked_addresses = mocker.patch(
            "rewards.views.reclaimable_addresses", return_value=["ADDR1", "ADDR2"]
        )
        request = rf.get(reverse("reclaim_allocations"))
        request.user = superuser
        response = ReclaimAllocationsView.as_view()(request)
        context = response.context_data
        assert context["addresses"] == ["ADDR1", "ADDR2"]
        mocked_addresses.assert_called_once_with()

    @pytest.mark.django_db
    def test_reclaimallocationsview_context_contains_use_admin_account(
        self, rf, superuser, mocker
    ):
        """Ensure addresses are added to context."""
        # Mock database call
        mocked_admin = mocker.patch("rewards.views.is_admin_account_configured")
        mocker.patch(
            "rewards.views.reclaimable_addresses", return_value=["ADDR1", "ADDR2"]
        )
        request = rf.get(reverse("reclaim_allocations"))
        request.user = superuser
        response = ReclaimAllocationsView.as_view()(request)
        context = response.context_data
        assert context["use_admin_account"] == mocked_admin.return_value
        mocked_admin.assert_called_once_with()

    # # post
    @pytest.mark.django_db
    def test_reclaimallocationsview_post_admin_account_not_configured(
        self, client, superuser, mocker
    ):
        """Test post when admin account is not configured."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=False)
        client.force_login(superuser)
        response = client.post(
            reverse("reclaim_allocations"),
            {"address": "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"},
        )
        assert response.status_code == 204
        assert response["HX-Redirect"] == reverse("reclaim_allocations")
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        assert any(
            "Admin account not configured" in str(message) for message in messages
        )

    @pytest.mark.django_db
    def test_reclaimallocationsview_post_missing_address(
        self, client, superuser, mocker
    ):
        """Test post when address is missing from request."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        client.force_login(superuser)
        response = client.post(
            reverse("reclaim_allocations"), {}
        )  # No address provided
        assert response.status_code == 204
        assert response["HX-Redirect"] == reverse("reclaim_allocations")
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        assert any("Missing reclaim address" in str(message) for message in messages)

    @pytest.mark.django_db
    def test_reclaimallocationsview_post_empty_address(self, client, superuser, mocker):
        """Test post when address is empty string."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        client.force_login(superuser)
        response = client.post(reverse("reclaim_allocations"), {"address": ""})
        assert response.status_code == 204
        assert response["HX-Redirect"] == reverse("reclaim_allocations")
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        assert any("Missing reclaim address" in str(message) for message in messages)

    @pytest.mark.django_db
    def test_reclaimallocationsview_post_successful_reclaim(
        self, client, superuser, mocker
    ):
        """Test successful allocation reclaim."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        # Mock the reclaim process to return a transaction ID
        mock_reclaim = mocker.patch(
            "rewards.views.process_reclaim_allocation", return_value="tx_hash_123"
        )
        # Mock user profile logging
        mock_profile = mocker.MagicMock()
        mocker.patch.object(User, "profile", mock_profile)
        client.force_login(superuser)
        response = client.post(
            reverse("reclaim_allocations"),
            {"address": "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"},
        )
        assert response.status_code == 204
        assert response["HX-Redirect"] == reverse("reclaim_allocations")
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        message_texts = [str(msg) for msg in messages]
        assert any(
            (
                "✅ Successfully reclaimed "
                "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU "
                "(TXID: tx_hash_123)"
            )
            in msg
            for msg in message_texts
        )
        # Verify reclaim was called with correct address
        mock_reclaim.assert_called_once_with(
            "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
        )
        # Verify log action was called
        mock_profile.log_action.assert_called_once_with(
            "allocation_reclaimed",
            "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU",
        )

    @pytest.mark.django_db
    def test_reclaimallocationsview_post_reclaim_failure(
        self, client, superuser, mocker
    ):
        """Test when allocation reclaim fails with exception."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        # Mock the reclaim process to raise an exception
        mock_reclaim = mocker.patch(
            "rewards.views.process_reclaim_allocation",
            side_effect=Exception("Contract execution reverted"),
        )
        # Mock user profile logging
        mock_profile = mocker.MagicMock()
        mocker.patch.object(User, "profile", mock_profile)
        client.force_login(superuser)
        response = client.post(
            reverse("reclaim_allocations"),
            {"address": "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"},
        )
        assert response.status_code == 204
        assert response["HX-Redirect"] == reverse("reclaim_allocations")
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        message_texts = [str(msg) for msg in messages]
        assert any(
            (
                "❌ Failed reclaiming allocation for "
                "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
                ": Contract execution reverted"
            )
            in msg
            for msg in message_texts
        )
        # Verify reclaim was called with correct address
        mock_reclaim.assert_called_once_with(
            "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
        )
        # Verify log action was NOT called on failure
        mock_profile.log_action.assert_not_called()

    @pytest.mark.django_db
    def test_reclaimallocationsview_post_specific_exception_handling(
        self, client, superuser, mocker
    ):
        """Test handling of specific exception types."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        # Test with different exception types
        test_cases = [
            (
                ValueError("Invalid address format"),
                (
                    "❌ Failed reclaiming allocation for "
                    "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
                    ": Invalid address format"
                ),
            ),
            (
                RuntimeError("Network error"),
                (
                    "❌ Failed reclaiming allocation for "
                    "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
                    ": Network error"
                ),
            ),
            (
                Exception("Generic error"),
                (
                    "❌ Failed reclaiming allocation for "
                    "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
                    ": Generic error"
                ),
            ),
        ]
        for exception, expected_message in test_cases:
            mocker.patch(
                "rewards.views.process_reclaim_allocation", side_effect=exception
            )
            client.force_login(superuser)
            data = {
                "address": "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"
            }
            response = client.post(reverse("reclaim_allocations"), data)
            assert response.status_code == 204
            assert response["HX-Redirect"] == reverse("reclaim_allocations")
            # Check error message contains the exception message
            messages = list(get_messages(response.wsgi_request))
            message_texts = [str(msg) for msg in messages]
            assert any(expected_message in msg for msg in message_texts)

    @pytest.mark.django_db
    def test_reclaimallocationsview_post_normal_user_blocked(
        self, client, user, mocker
    ):
        """Test that normal users cannot access post method."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        client.force_login(user)
        response = client.post(
            reverse("reclaim_allocations"),
            {"address": "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"},
        )
        # Should be redirected or forbidden
        assert response.status_code in (302, 403)

    @pytest.mark.django_db
    def test_reclaimallocationsview_post_anonymous_user_blocked(self, client, mocker):
        """Test that anonymous users cannot access post method."""
        mocker.patch("rewards.views.is_admin_account_configured", return_value=True)
        response = client.post(
            reverse("reclaim_allocations"),
            {"address": "2EVGZ4BGOSL3J64UYDE2BUGTNTBZZZLI54VUQQNZZLYCDODLY33UGXNSIU"},
        )
        # Should be redirected to login
        assert response.status_code == 302
        assert "/login" in response.url
