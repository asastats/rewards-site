"""Module containing base class for Rewards Suite website functional tests."""

import platform

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

SOCIAL_PROVIDERS = list(settings.SOCIALACCOUNT_PROVIDERS.keys())


class SeleniumTestCase(StaticLiveServerTestCase):
    """
    Automatically chooses between Chrome (x86_64) and Chromium (arm64).
    Works across Linux/macOS/CI.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        is_arm = platform.machine() in ("aarch64", "arm64")

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        if is_arm:
            print("Detected ARM64 → Using Chromium")
            service = Service("/usr/bin/chromedriver")

        else:
            print("Using Google Chrome (x86_64)")
            # WebDriver Manager for Chrome
            service = Service(ChromeDriverManager().install())

        cls.driver = webdriver.Chrome(
            service=service,
            options=chrome_options,
        )

        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "driver"):
            cls.driver.quit()
        super().tearDownClass()

    def get_url(self, path: str) -> str:
        """
        Helper to build full URLs.
        """
        if path.startswith("http"):
            return path
        return f"{self.live_server_url.rstrip('/')}/{path.lstrip('/')}"

    def prepare_for_htmx(self):
        """Install HTMX event listener BEFORE navigating."""
        self.driver.get(self.get_url("/"))
        self.driver.execute_script(
            """
            window._htmxAfterSwap = false;
            document.body.addEventListener('htmx:afterSwap', () => {
                window._htmxAfterSwap = true;
            });
        """
        )

    def safe_click(self, xpath):
        """Re-find element before clicking to avoid stale references."""
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        el = self.driver.find_element(By.XPATH, xpath)
        self.driver.execute_script("arguments[0].scrollIntoView(true);", el)
        el.click()

    def wait_for_htmx_swap(self):
        """Wait until HTMX finishes the swap."""
        WebDriverWait(self.driver, 5).until(
            lambda d: d.execute_script("return window._htmxAfterSwap === true;")
        )

    def wait_for_sidebar(self):
        """Ensure the sidebar and its navigation section are fully rendered."""
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class, 'drawer-side')]")
            )
        )
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//li[contains(@class, 'menu-title')][contains(., 'Main Navigation')]",
                )
            )
        )
