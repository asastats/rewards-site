"""Module containing website's URL configuration."""

from django.urls import path

from core import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("profile/", views.ProfileEditView.as_view(), name="profile"),
    path(
        "profile/deactivate/",
        views.DeactivateProfileView.as_view(),
        name="deactivate_profile",
    ),
    path("cycles/", views.CycleListView.as_view(), name="cycles"),
    path("cycle/<int:pk>", views.CycleDetailView.as_view(), name="cycle_detail"),
    path("contributors/", views.ContributorListView.as_view(), name="contributors"),
    path(
        "contributor/<int:pk>",
        views.ContributorDetailView.as_view(),
        name="contributor_detail",
    ),
    path(
        "contribution/<int:pk>",
        views.ContributionDetailView.as_view(),
        name="contribution_detail",
    ),
    path(
        "contribution/<int:pk>/edit/",
        views.ContributionEditView.as_view(),
        name="contribution_edit",
    ),
    path(
        "contribution/<int:pk>/invalidate/<str:reaction>",
        views.ContributionInvalidateView.as_view(),
        name="contribution_invalidate",
    ),
    path(
        "contribution/add/",
        views.ContributionCreateView.as_view(),
        name="contribution_add",
    ),
    path(
        "contribution/add/<int:issue_number>/",
        views.ContributionCreateView.as_view(),
        name="contribution_add_from_issue",
    ),
    path("issues/", views.IssueListView.as_view(), name="issues"),
    path(
        "create-issue/<int:contribution_id>",
        views.CreateIssueView.as_view(),
        name="create_issue",
    ),
    path(
        "issue/<int:pk>",
        views.IssueDetailView.as_view(),
        name="issue_detail",
    ),
    path("issue/<int:pk>/modal/", views.IssueModalView.as_view(), name="issue_modal"),
    path(
        "unconfirmed-contributions/",
        views.UnconfirmedContributionsView.as_view(),
        name="unconfirmed_contributions",
    ),
]
