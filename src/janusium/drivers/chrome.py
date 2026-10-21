from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from src.libs.SeleniumConnectPy.drivers.selenium import SeleniumDriver


class ChromeDriver(SeleniumDriver):
    """
    Standard Google Chrome WebDriver.

    Wraps ``selenium.webdriver.Chrome`` and manages the chromedriver binary
    automatically through ``webdriver-manager``.

    Anti-detection measures applied at launch:

    - ``--disable-blink-features=AutomationControlled`` removes the
      ``navigator.webdriver`` flag.
    - ``excludeSwitches: ["enable-automation"]`` hides the automation banner.
    - A realistic ``User-Agent`` string is injected via Chrome options.
    - ``navigator.webdriver``, ``navigator.languages``, and
      ``navigator.plugins`` are patched via CDP on every new document.

    Inherits all network filtering capabilities from
    :class:`~SeleniumConnectPy.drivers.selenium.SeleniumDriver`:
    use :attr:`NETWORK_BLOCKED_EXTENSIONS` and
    :attr:`NETWORK_DOMAIN_WHITELIST` to restrict outbound requests.
    """

    _driver_type = "Chrome"
    DEFAULT_ARGUMENTS = (
        "--disable-blink-features=AutomationControlled", "--window-size=1920,1080",
        "--start-maximized", "--no-sandbox", "--disable-dev-shm-usage",
        "--disable-extensions", "--disable-infobars",
    )
    HEADLESS_ARGUMENT = "--headless=new"

    def _launch_browser(self):
        """
        Instantiates a ``selenium.webdriver.Chrome`` instance with
        anti-detection options, download preferences, and active network
        filters.

        Steps performed:

        1. Builds ``ChromeOptions`` with stealth arguments and a realistic
           ``User-Agent``.
        2. Applies the domain whitelist via ``--host-rules`` if
           :attr:`NETWORK_DOMAIN_WHITELIST` is set.
        3. Configures automatic file downloads to
           :attr:`~SeleniumDriver.download_tmp_directory`.
        4. Installs the matching chromedriver binary via
           ``ChromeDriverManager`` and creates the ``Chrome`` instance.
        5. Applies extension-based request blocking via CDP
           (:meth:`~SeleniumDriver._setup_network_extension_filter`).
        6. Overrides ``navigator.webdriver``, ``navigator.languages``, and
           ``navigator.plugins`` via ``Page.addScriptToEvaluateOnNewDocument``
           to reduce the automation fingerprint.
        """
        options = webdriver.ChromeOptions()

        for argument in (*self._iter_browser_arguments(), f"--user-agent={self.get_random_user_agent()}"):
            options.add_argument(argument)
        host_rules = self._build_host_rules_argument()
        if host_rules:
            options.add_argument(f"--host-rules={host_rules}")

        download_directory = self.download_tmp_directory.replace("/", "\\")
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": rf"{download_directory}",
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "profile.default_content_setting_values.automatic_downloads": 1,
            },
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        self._browser = webdriver.Chrome(service=service, options=options)
        self._setup_network_extension_filter()
        self._browser.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['es-ES', 'es', 'en-US', 'en']
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                """
            },
        )
