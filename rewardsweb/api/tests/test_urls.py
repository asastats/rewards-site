"""Testing module for :py:mod:`api.urls` module."""

from django.urls import URLPattern

from api import urls


class TestApiUrls:
    """Testing class for :py:mod:`api.urls` module."""

    def _url_from_pattern(self, pattern):
        """Helper method to find URL pattern by string pattern."""
        return next(url for url in urls.urlpatterns if str(url.pattern) == pattern)

    def test_api_urls_contributions(self):
        """Test contributions endpoint URL configuration."""
        url = self._url_from_pattern("contributions")
        assert isinstance(url, URLPattern)
        assert url.name == "contributions"
        # Check that callback has view_class attribute for class-based views
        assert hasattr(url.callback, "view_class")
        assert url.callback.view_class.__name__ == "ContributionsView"

    def test_api_urls_cycle_by_id_plain(self):
        """Test cycle by ID plain endpoint URL configuration."""
        url = self._url_from_pattern("cycles/<int:cycle_id>/plain")
        assert isinstance(url, URLPattern)
        assert url.name == "cycle-by-id-plain"
        assert hasattr(url.callback, "view_class")
        assert url.callback.view_class.__name__ == "CyclePlainView"

    def test_api_urls_cycle_by_id_aggregated(self):
        """Test cycle by ID aggregated endpoint URL configuration."""
        url = self._url_from_pattern("cycles/<int:cycle_id>")
        assert isinstance(url, URLPattern)
        assert url.name == "cycle-by-id"
        assert hasattr(url.callback, "view_class")
        assert url.callback.view_class.__name__ == "CycleAggregatedView"

    def test_api_urls_cycle_current_plain(self):
        """Test current cycle plain endpoint URL configuration."""
        url = self._url_from_pattern("cycles/current/plain")
        assert isinstance(url, URLPattern)
        assert url.name == "cycle-current-plain"
        assert hasattr(url.callback, "view_class")
        assert url.callback.view_class.__name__ == "CurrentCyclePlainView"

    def test_api_urls_cycle_current_aggregated(self):
        """Test current cycle aggregated endpoint URL configuration."""
        url = self._url_from_pattern("cycles/current")
        assert isinstance(url, URLPattern)
        assert url.name == "cycle-current"
        assert hasattr(url.callback, "view_class")
        assert url.callback.view_class.__name__ == "CurrentCycleAggregatedView"

    def test_api_urls_contributions_tail(self):
        """Test contributions tail endpoint URL configuration."""
        url = self._url_from_pattern("contributions/tail")
        assert isinstance(url, URLPattern)
        assert url.name == "contributions-tail"
        assert hasattr(url.callback, "view_class")
        assert url.callback.view_class.__name__ == "ContributionsTailView"

    def test_api_urls_add_contribution(self):
        """Test add contribution endpoint URL configuration."""
        url = self._url_from_pattern("addcontribution")
        assert isinstance(url, URLPattern)
        assert url.name == "add-contribution"
        assert hasattr(url.callback, "view_class")
        assert url.callback.view_class.__name__ == "AddContributionView"

    def test_api_urls_add_issue(self):
        """Test add issue endpoint URL configuration."""
        url = self._url_from_pattern("addissue")
        assert isinstance(url, URLPattern)
        assert url.name == "add-issue"
        assert hasattr(url.callback, "view_class")
        assert url.callback.view_class.__name__ == "AddIssueView"

    def test_api_urls_pattern_count(self):
        """Test that all expected URL patterns are present."""
        assert len(urls.urlpatterns) == 8

    def test_api_urls_all_patterns_are_urlpatterns(self):
        """Test that all URL patterns are valid URLPattern instances."""
        for url in urls.urlpatterns:
            assert isinstance(url, URLPattern)

    def test_api_urls_all_patterns_have_names(self):
        """Test that all URL patterns have names assigned."""
        for url in urls.urlpatterns:
            assert url.name is not None
            assert url.name != ""

    def test_api_urls_all_callbacks_have_view_class(self):
        """Test that all URL callbacks are class-based views."""
        for url in urls.urlpatterns:
            assert hasattr(
                url.callback, "view_class"
            ), f"URL {url.pattern} callback has no view_class"
