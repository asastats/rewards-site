"""Testing module for website's URL dispatcher module."""

from django.urls import URLPattern, URLResolver

from rewardsweb import urls


class TestRewardsWebUrls:
    """Testing class for :py:mod:`rewardsweb.urls` module."""

    def _url_from_pattern(self, pattern):
        return next(url for url in urls.urlpatterns if str(url.pattern) == pattern)

    def test_rewardsweb_urls_admin_app(self):
        url = self._url_from_pattern("admin/")
        assert isinstance(url, URLResolver)
        assert url.namespace == "admin"

    def test_rewardsweb_urls_api_wallet(self):
        url = self._url_from_pattern("api/wallet/")
        assert isinstance(url, URLResolver)
        assert "walletauth.urls" in str(url.urlconf_name)

    def test_rewardsweb_urls_api(self):
        url = self._url_from_pattern("api/")
        assert isinstance(url, URLResolver)
        assert "api.urls" in str(url.urlconf_name)

    def test_rewardsweb_urls_custom_login(self):
        url = self._url_from_pattern("accounts/login/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.LoginView"
        assert url.name == "account_login"

    def test_rewardsweb_urls_custom_signup(self):
        url = self._url_from_pattern("accounts/signup/")
        assert isinstance(url, URLPattern)
        assert url.lookup_str == "core.views.SignupView"
        assert url.name == "account_signup"

    def test_rewardsweb_urls_allauth_app(self):
        url = self._url_from_pattern("accounts/")
        assert isinstance(url, URLResolver)
        assert "allauth.urls" in str(url.urlconf_name)

    def test_rewardsweb_urls_captcha(self):
        url = self._url_from_pattern("captcha/")
        assert isinstance(url, URLResolver)
        assert "captcha.urls" in str(url.urlconf_name)

    def test_rewardsweb_urlsrewards_app(self):
        url = self._url_from_pattern("rewards/")
        assert isinstance(url, URLResolver)
        assert "rewards.urls" in str(url.urlconf_name)

    def test_rewardsweb_urls_core_app(self):
        url = self._url_from_pattern("")
        assert isinstance(url, URLResolver)
        assert "core.urls" in str(url.urlconf_name)

    def test_rewardsweb_urls_pattern_count(self):
        assert len(urls.urlpatterns) == 11
