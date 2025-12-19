"""Module containing the views for the rewards app."""

from algosdk.encoding import is_valid_address
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from contract.helpers import is_admin_account_configured
from contract.network import (
    claimable_amount_for_address,
    process_allocations_for_contributions,
    process_reclaim_allocation,
    reclaimable_addresses,
)
from core.models import Contribution, IssueStatus
from rewards.helpers import (
    added_allocations_for_addresses,
    reclaimed_allocation_for_address,
)


class ClaimView(LoginRequiredMixin, TemplateView):
    """View for users to claim their rewards.

    This view displays the claim rewards interface, which allows authenticated
    users to initiate the process of claiming their earned rewards.
    """

    template_name = "rewards/claim.html"

    def get_context_data(self, **kwargs):
        """Add claimable status to the context.

        This method determines if the current user has a claimable allocation
        and adds a boolean `claimable` to the context.

        :param kwargs: Additional keyword arguments
        :return: Context dictionary with claimable status
        :var context: data to use in template
        :type context: dict
        :var amount: amount to claim by the user
        :type amount: dict
        :rtype: dict
        """
        context = super().get_context_data(**kwargs)
        context["amount"] = 0

        contributor = getattr(self.request.user.profile, "contributor", None)
        if (
            contributor
            and contributor.address
            and is_valid_address(contributor.address)
        ):
            try:
                amount = claimable_amount_for_address(contributor.address)

            except ValueError:
                amount = 0

            context["amount"] = amount

        return context


@method_decorator(user_passes_test(lambda user: user.is_superuser), name="dispatch")
class AddAllocationsView(LoginRequiredMixin, TemplateView):
    """View for superusers to add new allocations.

    This view provides an interface for users with superuser privileges to add
    new reward allocations to the smart contract. It is restricted to
    superusers to prevent unauthorized modifications.
    """

    template_name = "rewards/add_allocations.html"

    def get_context_data(self, **kwargs):
        """Add any necessary context for the add allocations page.

        :param kwargs: Additional keyword arguments
        :return: Context dictionary
        :rtype: dict
        """
        context = super().get_context_data(**kwargs)
        addresses, amounts = (
            Contribution.objects.addressed_contributions_addresses_and_amounts()
        )
        if addresses:
            context["allocations"] = zip(addresses, amounts)
            context["use_admin_account"] = is_admin_account_configured()

        return context

    def post(self, request, *args, **kwargs):
        """Run contract allocation batching when admin account is available.

        :param request: HTTP request object
        :type request: :class:`rest_framework.request.Request`
        :return: :class:`django.http.HttpResponse`
        """
        use_admin_account = is_admin_account_configured()

        if not use_admin_account:
            messages.error(request, "Admin account not configured.")
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("add_allocations")
            return response

        contributions = Contribution.objects.filter(issue__status=IssueStatus.ADDRESSED)

        # Run allocations in batches — generator yields results per batch
        for result, payload in process_allocations_for_contributions(
            contributions,
            Contribution.objects.addresses_and_amounts_from_contributions,
        ):
            if result:
                added_allocations_for_addresses(request, payload, result)

            else:
                messages.error(request, f"❌ {payload[0]}")
                break

        else:
            messages.info(request, "✅ All batches completed.")

        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("add_allocations")
        return response


@method_decorator(user_passes_test(lambda user: user.is_superuser), name="dispatch")
class ReclaimAllocationsView(LoginRequiredMixin, TemplateView):
    """View for superusers to reclaim allocations.

    This view allows superusers to reclaim reward allocations from the smart
    contract. This is typically done for allocations that are no longer valid
    or need to be returned. Access is restricted to superusers.
    """

    template_name = "rewards/reclaim_allocations.html"

    def get_context_data(self, **kwargs):
        """Add any necessary context for the reclaim allocations page.

        :param kwargs: Additional keyword arguments
        :return: Context dictionary
        :rtype: dict
        """
        context = super().get_context_data(**kwargs)
        context["addresses"] = reclaimable_addresses()
        context["use_admin_account"] = is_admin_account_configured()
        return context

    def post(self, request, *args, **kwargs):
        """Handle individual allocation reclaim request.

        :param request: HTTP request object
        :type request: :class:`rest_framework.request.Request`
        :return: :class:`django.http.HttpResponse`
        """
        if not is_admin_account_configured():
            messages.error(request, "Admin account not configured.")
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("reclaim_allocations")
            return response

        address = request.POST.get("address")

        if not address:
            messages.error(request, "Missing reclaim address.")
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("reclaim_allocations")
            return response

        try:
            txid = process_reclaim_allocation(address)
            reclaimed_allocation_for_address(request, address, txid)

        except Exception as e:
            messages.error(
                request, f"❌ Failed reclaiming allocation for {address}: {e}"
            )

        # ✅ HTMX full refresh so messages appear automatically
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("reclaim_allocations")
        return response
