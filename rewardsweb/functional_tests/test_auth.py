"""Module containing authentication functional tests."""

from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from functional_tests.base import SOCIAL_PROVIDERS, SeleniumTestCase


class CommonAuthTests(SeleniumTestCase):
    """
    Base class providing shared tests for /accounts/login/ and /accounts/signup/.

    Subclasses must define:
        self.page_name  -> ("account_login" or "account_signup")
    """

    __test__ = False  # Prevent pytest / unittest from discovering this class as tests

    page_name = None  # must be overridden by subclasses

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        assert cls.page_name is not None, "Subclasses must set page_name"
        cls.page_url = reverse(cls.page_name)

    def setUp(self):
        super().setUp()
        self.driver.get(self.get_url(self.page_url))

    #
    # --- NETWORK TESTS (common)
    #
    def test_network_initial(self):
        badge = self.driver.find_element(By.ID, "network-name")
        assert "testnet" in badge.text.lower()

    def test_network_switch(self):
        main_btn = self.driver.find_element(
            By.XPATH, "//button[@data-network='mainnet']"
        )
        main_btn.click()
        badge = self.driver.find_element(By.ID, "network-name")
        assert "mainnet" in badge.text.lower()

        test_btn = self.driver.find_element(
            By.XPATH, "//button[@data-network='testnet']"
        )
        test_btn.click()
        badge = self.driver.find_element(By.ID, "network-name")
        assert "testnet" in badge.text.lower()

    #
    # --- WALLET TESTS (common)
    #
    def _get_wallet_ids(self):
        blocks = self.driver.find_elements(By.CSS_SELECTOR, "div[id^='wallet-']")
        return [b.get_attribute("id").replace("wallet-", "", 1) for b in blocks]

    def _assert_wallet_buttons(self, wid):
        connect_btn = self.driver.find_element(By.ID, f"connect-button-{wid}")
        assert connect_btn.is_displayed()

        hidden_ids = [
            f"disconnect-button-{wid}",
            f"transaction-button-{wid}",
            f"auth-button-{wid}",
            f"set-active-button-{wid}",
        ]
        for hid in hidden_ids:
            el = self.driver.find_element(By.ID, hid)
            assert not el.is_displayed()

        select = self.driver.find_element(By.ID, f"active-account-select-{wid}")
        options = select.find_elements(By.TAG_NAME, "option")
        assert len(options) == 1
        assert "No accounts" in options[0].text

    def test_wallets_have_correct_buttons(self):
        wallet_ids = self._get_wallet_ids()
        assert wallet_ids, f"Wallet providers missing on {self.page_name}"

        for wid in wallet_ids:
            self._assert_wallet_buttons(wid)

    #
    # --- SOCIAL PROVIDER BUTTONS (common)
    #
    def test_social_provider_buttons_exist(self):
        for pid in SOCIAL_PROVIDERS:
            xpath = f"//a[contains(@href, '/accounts/{pid}/login/?process=login')]"
            btn = self.driver.find_element(By.XPATH, xpath)
            assert btn.is_displayed()

    def test_social_provider_button_text(self):
        for pid in SOCIAL_PROVIDERS:
            xpath = f"//a[contains(@href, '/accounts/{pid}/login/?process=login')]"
            btn = self.driver.find_element(By.XPATH, xpath)
            assert "Continue with" in btn.text

    #
    # --- PASSKEY TESTS (common)
    #
    def test_passkey_button_exists_if_enabled(self):
        buttons = self.driver.find_elements(By.ID, "passkey_login")
        if not buttons:
            return
        assert buttons[0].is_displayed()

    def test_passkey_button_triggers_script(self):
        buttons = self.driver.find_elements(By.ID, "passkey_login")
        if not buttons:
            return

        buttons[0].click()

        script = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "//script[contains(@src,'login_script')]")
            )
        )
        assert script is not None

    #
    # --- NAVIGATION LINKS (distinct expectations per page)
    #
    def test_navigation_links(self):
        page = self.page_name

        if page == "account_login":
            # Should have link to signup
            link = self.driver.find_element(
                By.XPATH, "//a[contains(@href,'/accounts/signup/')]"
            )
            link.click()
            assert "Create Your Account" in self.driver.page_source

        if page == "account_signup":
            # Should have link back to login
            link = self.driver.find_element(
                By.XPATH, "//a[contains(., 'Sign in here')]"
            )
            link.click()
            assert "Welcome Back" in self.driver.page_source

        # Both pages have "Back to Home"
        self.driver.get(self.get_url(self.page_url))
        home = self.driver.find_element(By.XPATH, "//a[contains(., 'Back to Home')]")
        home.click()
        assert "{{ PROJECT_NAME }}" in self.driver.page_source

    #
    # --- VALIDATION TESTS
    #
    def test_validation_errors_appear(self):
        """
        Only the SIGNUP page shows field-level validation errors.
        Login page DOES NOT have required fields → no errors.
        """
        page = self.page_name

        submit = self.driver.find_element(By.XPATH, "//button[@type='submit']")
        submit.click()

        if page == "account_signup":
            errors = self.driver.find_elements(By.CSS_SELECTOR, ".text-error")
            assert errors, "Signup page should display field-level validation errors."

        if page == "account_login":
            # Login page should NOT show validation errors unless custom fields exist
            errors = self.driver.find_elements(
                By.CSS_SELECTOR, ".text-error, .alert-error"
            )
            assert not errors, "Login page should not show validation errors."


class LoginPageTests(CommonAuthTests):
    page_name = "account_login"


class LoginPageLinkTests(LoginPageTests):

    def test_link_to_signup(self):
        link = self.driver.find_element(
            By.XPATH, "//a[contains(@href, '/accounts/signup/')]"
        )
        link.click()
        assert "Create Your Account" in self.driver.page_source

    def test_link_to_reset_password(self):
        link = self.driver.find_element(
            By.XPATH, "//a[contains(@href, '/accounts/password/reset/')]"
        )
        link.click()
        assert "Enter your email address" in self.driver.page_source

    def test_link_back_to_home(self):
        link = self.driver.find_element(By.XPATH, "//a[contains(., 'Back to Home')]")
        link.click()
        assert "{{ PROJECT_NAME }}" in self.driver.page_source


class SignupPageTests(CommonAuthTests):
    page_name = "account_signup"


class SignupPageValidationTests(SignupPageTests):

    def test_empty_form_shows_errors(self):
        submit = self.driver.find_element(By.XPATH, "//button[@type='submit']")
        submit.click()

        # Wait for field-level errors to appear
        errors = self.driver.find_elements(By.CSS_SELECTOR, ".text-error")
        assert errors, "Expected field-level errors, but found none."


class SignupPageLinkTests(SignupPageTests):

    def test_back_to_login(self):
        link = self.driver.find_element(By.XPATH, "//a[contains(., 'Sign in here')]")
        link.click()
        assert "Welcome Back" in self.driver.page_source

    def test_back_to_home(self):
        link = self.driver.find_element(By.XPATH, "//a[contains(., 'Back to Home')]")
        link.click()
        assert "{{ PROJECT_NAME }}" in self.driver.page_source
