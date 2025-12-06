"""Testing module for core app's URL dispatcher module."""

from django.urls import URLPattern

from core import urls


class TestCoreUrls:
    """Testing class for :py:mod:`core.urls` module."""

    def _url_from_pattern(self, pattern):
        return next(url for url in urls.urlpatterns if str(url.pattern) == pattern)

    def test_core_urls_index(self):
        url = self._url_from_pattern("")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.IndexView"
        assert url.name == "index"

    def test_core_urls_profile(self):
        url = self._url_from_pattern("profile/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.ProfileEditView"
        assert url.name == "profile"

    def test_core_urls_deactivate_profile(self):
        url = self._url_from_pattern("profile/deactivate/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.DeactivateProfileView"
        assert url.name == "deactivate_profile"

    def test_core_urls_cycles(self):
        url = self._url_from_pattern("cycles/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.CycleListView"
        assert url.name == "cycles"

    def test_core_urls_cycle_detail(self):
        url = self._url_from_pattern("cycle/<int:pk>")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.CycleDetailView"
        assert url.name == "cycle_detail"

    def test_core_urls_contributors(self):
        url = self._url_from_pattern("contributors/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.ContributorListView"
        assert url.name == "contributors"

    def test_core_urls_contributor_detail(self):
        url = self._url_from_pattern("contributor/<int:pk>")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.ContributorDetailView"
        assert url.name == "contributor_detail"

    def test_core_urls_contribution_detail(self):
        url = self._url_from_pattern("contribution/<int:pk>")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.ContributionDetailView"
        assert url.name == "contribution_detail"

    def test_core_urls_contribution_edit(self):
        url = self._url_from_pattern("contribution/<int:pk>/edit/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.ContributionEditView"
        assert url.name == "contribution_edit"

    def test_core_urls_contribution_invalidate(self):
        url = self._url_from_pattern("contribution/<int:pk>/invalidate/<str:reaction>")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.ContributionInvalidateView"
        assert url.name == "contribution_invalidate"

    def test_core_urls_contribution_add(self):
        url = self._url_from_pattern("contribution/add/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.ContributionCreateView"
        assert url.name == "contribution_add"

    def test_core_urls_contribution_add_from_issue(self):
        url = self._url_from_pattern("contribution/add/<int:issue_number>/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.ContributionCreateView"
        assert url.name == "contribution_add_from_issue"

    def test_core_urls_issues(self):
        url = self._url_from_pattern("issues/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.IssueListView"
        assert url.name == "issues"

    def test_core_urls_create_issue(self):
        url = self._url_from_pattern("create-issue/<int:contribution_id>")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.CreateIssueView"
        assert url.name == "create_issue"

    def test_core_urls_issue_detail(self):
        url = self._url_from_pattern("issue/<int:pk>")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.IssueDetailView"
        assert url.name == "issue_detail"

    def test_core_urls_issue_modal(self):
        url = self._url_from_pattern("issue/<int:pk>/modal/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.IssueModalView"
        assert url.name == "issue_modal"

    def test_core_urls_unconfirmed_contributions(self):
        url = self._url_from_pattern("unconfirmed-contributions/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.UnconfirmedContributionsView"
        assert url.name == "unconfirmed_contributions"

    def test_core_urls_transparency(self):
        url = self._url_from_pattern("transparency/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.TransparencyReportView"
        assert url.name == "transparency"

    def test_core_urls_refresh_transparency_data(self):
        url = self._url_from_pattern("transparency/refresh/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.RefreshTransparencyDataView"
        assert url.name == "refresh_transparency_data"

    def test_core_urls_patterns_count(self):
        assert len(urls.urlpatterns) == 19
