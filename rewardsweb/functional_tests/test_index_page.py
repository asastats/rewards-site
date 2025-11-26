"""Module containing functional tests for the website's index page."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from functional_tests.base import SeleniumTestCase

User = get_user_model()


class IndexPageAnonymousTests(SeleniumTestCase):

    def test_index_page_loads_and_has_correct_title(self):
        url = self.get_url(reverse("index"))
        self.driver.get(url)

        self.assertEqual(self.driver.title, "ASA Stats Rewards Suite website")

        h1 = self.driver.find_element(By.TAG_NAME, "h1")
        self.assertIn("ASA Stats Rewards", h1.text)

    def test_navbar_shows_login(self):
        url = self.get_url(reverse("index"))
        self.driver.get(url)

        login_button = self.driver.find_element(By.LINK_TEXT, "Login")
        self.assertIn("Login", login_button.text)

    def test_quick_actions_login_button(self):
        url = self.get_url(reverse("index"))
        self.driver.get(url)

        qa_login = self.driver.find_element(
            By.XPATH, "//a[contains(@href, '/accounts/login/')][contains(., 'Login')]"
        )
        self.assertTrue(qa_login.is_displayed())

    def test_sidebar_logo_link(self):
        url = self.get_url(reverse("index"))
        self.driver.get(url)

        logo_link = self.driver.find_element(
            By.XPATH,
            "//div[contains(@class,'drawer-side')]//a[span[contains(., 'Rewards')]]",
        )
        self.assertIn("Rewards", logo_link.text)


class IndexPageLoginFormTests(SeleniumTestCase):

    def setUp(self):
        super().setUp()
        self.password = "secret123"
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password=self.password,
        )

    def test_login_via_form(self):
        login_url = self.get_url(reverse("account_login"))
        index_url = self.get_url(reverse("index"))

        self.driver.get(login_url)

        self.driver.find_element(By.NAME, "login").send_keys(self.user.username)
        self.driver.find_element(By.NAME, "password").send_keys(self.password)

        submit = self.driver.find_element(
            By.XPATH, "//form[@method='post']//button[@type='submit']"
        )
        submit.click()

        self.driver.implicitly_wait(2)
        self.assertTrue(self.driver.current_url.startswith(index_url))

        badge = self.driver.find_element(
            By.XPATH, f"//span[contains(., '{self.user.username}')]"
        )
        self.assertTrue(badge.is_displayed())


class IndexPageAuthenticatedTests(SeleniumTestCase):

    def setUp(self):
        super().setUp()
        self.password = "secret123"
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password=self.password,
        )

    def _login(self):
        client = Client()
        client.login(username=self.user.username, password=self.password)
        cookie = client.cookies.get(settings.SESSION_COOKIE_NAME)

        self.driver.get(self.get_url("/"))
        self.driver.add_cookie(
            {
                "name": settings.SESSION_COOKIE_NAME,
                "value": cookie.value,
                "path": "/",
            }
        )

    def test_username_badge_appears(self):
        self._login()
        url = self.get_url(reverse("index"))
        self.driver.get(url)

        badge = self.driver.find_element(
            By.XPATH, f"//span[contains(., '{self.user.username}')]"
        )
        self.assertIn(self.user.username, badge.text)

    def test_quick_actions_visible(self):
        self._login()
        url = self.get_url(reverse("index"))
        self.driver.get(url)

        for name, label in [
            ("cycles", "View Cycles"),
            ("contributors", "Browse Contributors"),
            ("issues", "View"),
        ]:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        f"//a[contains(@href, '{reverse(name)}')][contains(., '{label}')]",
                    )
                )
            )
            el = self.driver.find_element(
                By.XPATH,
                f"//a[contains(@href, '{reverse(name)}')][contains(., '{label}')]",
            )
            self.assertTrue(el.is_displayed())

    def test_stats_cards_exist(self):
        url = self.get_url(reverse("index"))
        self.driver.get(url)

        # Wait for stat cards to render
        cards = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.stat-card"))
        )

        # We expect at least 4 stat cards
        self.assertGreaterEqual(len(cards), 4)

        # Now check for the actual headings *inside cards*
        headings = [
            "Total Cycles",
            "Contributors",
            "Contributions",
            "Total Rewards",
        ]

        for heading in headings:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        f"//div[contains(@class,'stat-card')]//*[contains(text(), '{heading}')]",
                    )
                )
            )


class IndexPageHTMXNavigationTests(SeleniumTestCase):

    def test_htmx_boost_avoids_full_reload(self):
        """
        Navigating with hx-boost should not reload the whole page,
        and HTMX should replace the <main> content only.
        """
        index_url = self.get_url(reverse("index"))
        contributors_url = reverse("contributors")

        # Load page and install reload detector BEFORE any navigation
        self.driver.get(index_url)
        self.driver.execute_script(
            """
            window.PAGE_RELOADED = false;
            window.addEventListener('beforeunload', () => {
                window.PAGE_RELOADED = true;
            });
        """
        )

        # First click, but do NOT rely on HTMX finish yet
        self.safe_click(f"//a[contains(@href, '{contributors_url}')]")

        # Check that the page did NOT fully reload
        reloaded = self.driver.execute_script("return window.PAGE_RELOADED;")
        self.assertFalse(reloaded, "Page should not full-reload with hx-boost.")

    def test_htmx_content_swaps_correctly(self):
        """
        Validate that the HTMX swap actually updates the <main> content
        and renders the Contributors page.
        """
        contributors_url = reverse("contributors")

        # Prepare HTMX listener BEFORE navigation
        self.prepare_for_htmx()

        # Trigger navigation
        self.safe_click(f"//a[contains(@href, '{contributors_url}')]")

        # Wait for HTMX completion
        self.wait_for_htmx_swap()

        # Now verify new content
        main_text = self.driver.find_element(By.TAG_NAME, "main").text
        self.assertIn(
            "Contributors",
            main_text,
            "HTMX navigation should load Contributors page content.",
        )
