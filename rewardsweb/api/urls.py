"""Module containing Rewards Suite API URL configuration."""

from django.urls import path

from api import views

urlpatterns = [
    path("contributions", views.ContributionsView.as_view(), name="contributions"),
    path(
        "cycles/<int:cycle_id>/plain",
        views.CyclePlainView.as_view(),
        name="cycle-by-id-plain",
    ),
    path(
        "cycles/<int:cycle_id>", views.CycleAggregatedView.as_view(), name="cycle-by-id"
    ),
    path(
        "cycles/current/plain",
        views.CurrentCyclePlainView.as_view(),
        name="cycle-current-plain",
    ),
    path(
        "cycles/current",
        views.CurrentCycleAggregatedView.as_view(),
        name="cycle-current",
    ),
    path(
        "contributions/tail",
        views.ContributionsTailView.as_view(),
        name="contributions-tail",
    ),
    path(
        "addcontribution", views.AddContributionView.as_view(), name="add-contribution"
    ),
    path("addissue", views.AddIssueView.as_view(), name="add-issue"),
]
