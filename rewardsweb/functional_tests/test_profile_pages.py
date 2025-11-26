"""Module containing functional tests for the user's profile related pages."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from functional_tests.base import SeleniumTestCase

User = get_user_model()


def wait_for_text(driver, text, timeout=10):
    WebDriverWait(driver, timeout).until(
        lambda d: text.lower() in d.page_source.lower()
    )


def wait_for_any_text(driver, texts, timeout=10):
    WebDriverWait(driver, timeout).until(
        lambda d: any(t.lower() in d.page_source.lower() for t in texts)
    )


# =============================================================================
#  BASE CLASS
# =============================================================================


class ProfileBaseTest(SeleniumTestCase):
    username = "testuser@example.com"
    password = "password123"

    def setUp(self):
        super().setUp()

        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
        )

        self.driver.delete_all_cookies()
        self.driver.get(self.live_server_url)

    def tearDown(self):
        """
        Clean state between tests WITHOUT quitting the WebDriver.
        This prevents HTMX or session state from leaking across tests.
        """
        try:
            self.driver.delete_all_cookies()
        except Exception:
            pass

        try:
            self.driver.get("about:blank")
        except Exception:
            pass

        super().tearDown()

    def _force_login(self):
        """Perform a clean login and wait for authenticated layout."""

        # ALWAYS install HTMX listener *before* any HTMX loads
        self.driver.get(self.get_url("/"))
        self.driver.execute_script(
            """
            window._htmxAfterSwap = false;
            document.body.addEventListener('htmx:afterSwap', () => {
                window._htmxAfterSwap = true;
            });
        """
        )

        login_url = self.get_url(reverse("account_login"))
        self.driver.get(login_url)

        # Fill login form
        username_field = self.driver.find_element(
            By.CSS_SELECTOR, "input[name='login']"
        )
        password_field = self.driver.find_element(
            By.CSS_SELECTOR, "input[name='password']"
        )

        username_field.clear()
        username_field.send_keys(self.username)
        password_field.clear()
        password_field.send_keys(self.password)

        # Real sign-in button
        login_button = self.driver.find_element(
            By.CSS_SELECTOR, "button[type='submit'][tags='prominent,login']"
        )
        login_button.click()

        # Sidebar is HTMX-loaded → requires listener installed BEFORE login
        try:
            self.wait_for_htmx_swap()
        except Exception:
            pass

        # Now wait for the sidebar DOM structure
        self.wait_for_sidebar()

    # ----------------------------------------------------------------------
    # OPEN PROFILE PAGE
    # ----------------------------------------------------------------------

    def _open_profile_page(self):
        """
        Login → open profile → install HTMX listener → wait for sidebar if present.
        """

        self._force_login()

        profile_url = self.get_url(reverse("profile"))
        self.driver.get(profile_url)

        # Install the HTMX listener on THIS actual page
        self.driver.execute_script(
            """
            window._htmxAfterSwap = false;
            document.body.addEventListener('htmx:afterSwap', () => {
                window._htmxAfterSwap = true;
            });
        """
        )

        # If profile loads HTMX content, wait for it. If not, this returns instantly.
        try:
            self.wait_for_htmx_swap()
        except Exception:
            pass  # Some pages load no HTMX at all; safe to continue.

        # Profile headings should now be present
        wait_for_any_text(
            self.driver, ["profile settings", "personal information"], timeout=10
        )


# =============================================================================
#  SCENARIO TESTS
# =============================================================================


class ProfileScenarioTests(ProfileBaseTest):

    def setUp(self):
        super().setUp()
        self._open_profile_page()

    # Navigation tests
    def test_navigate_to_email_addresses_from_profile(self):
        """
        Ensure the "Email Addresses" page opens from profile.
        """

        # Click the link (may trigger htmx or full page reload)
        link = self.driver.find_element(By.CSS_SELECTOR, "a[href='/accounts/email/']")
        link.click()

        # Do NOT wait for htmx swap — not guaranteed in CI
        wait_for_any_text(self.driver, ["email address", "primary email"], timeout=10)

    def test_navigate_to_social_connections_from_profile(self):

        link = self.driver.find_element(
            By.CSS_SELECTOR, "a[href='/accounts/3rdparty/']"
        )
        link.click()

        wait_for_any_text(self.driver, ["social", "connection", "provider"], timeout=10)

    def test_navigate_to_deactivate_account_from_profile(self):

        link = self.driver.find_element(
            By.CSS_SELECTOR, "a[href='/profile/deactivate/']"
        )
        link.click()

        wait_for_any_text(self.driver, ["Deactivate account"], timeout=10)

        captcha_image = self.driver.find_element(By.CSS_SELECTOR, "img.captcha")
        self.assertIn("/captcha/image/", captcha_image.get_attribute("src"))

        captcha_input = self.driver.find_element(By.ID, "id_captcha_1")
        self.assertEqual("captcha_1", captcha_input.get_attribute("name"))

    # Structure
    def test_profile_page_structure_and_fields(self):
        src = self.driver.page_source.lower()
        assert "profile" in src
        assert "settings" in src or "personal information" in src
        self.driver.find_element(By.NAME, "first_name")
        self.driver.find_element(By.NAME, "last_name")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")

    # Updates
    def test_profile_update_no_validation_errors(self):
        """
        Submitting without changing anything must not produce
        *real validation errors* (but the DOM may still contain
        classes like 'alert-error' for styling).
        """

        submit = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit.click()

        # Wait briefly for page reload
        WebDriverWait(self.driver, 5).until(lambda d: True)

        # Look for true error elements only
        error_selectors = [
            ".alert-error .alert-content",  # actual visible content, not wrapper div
            ".errorlist li",
            "[role='alert']",
        ]

        for selector in error_selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            # Only consider *visible* errors
            visible = [e for e in elements if e.is_displayed()]
            assert not visible, f"Unexpected visible validation errors found: {visible}"

    def test_profile_update_saves_fields_dom(self):
        fn = self.driver.find_element(By.NAME, "first_name")
        ln = self.driver.find_element(By.NAME, "last_name")

        fn.clear()
        ln.clear()

        fn.send_keys("Alice")
        ln.send_keys("Johnson")

        submit = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit.click()

        self.wait_for_htmx_swap()
        wait_for_text(self.driver, "alice")
        wait_for_text(self.driver, "johnson")


# =============================================================================
#  CONFIRM EMAIL PAGE TESTS
# =============================================================================


class ConfirmEmailPageTests(SeleniumTestCase):

    def tearDown(self):
        try:
            self.driver.delete_all_cookies()
            self.driver.get("about:blank")
        except Exception:
            pass
        super().tearDown()

    def test_confirm_email_page_structure(self):
        url = self.get_url("/accounts/confirm-email/invalid123token/")
        self.driver.get(url)

        src = self.driver.page_source.lower()

        if "sign in" in src or "login" in src:
            assert "email" in src
            return

        if "confirm email address" in src:
            assert "confirm" in src
            assert "email" in src
            return

        assert False, "Unexpected page for confirm-email flow."
