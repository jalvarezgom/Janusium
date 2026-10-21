import undetected_chromedriver as uc

from environment import Environment
from src.libs.SeleniumConnectPy.drivers.selenium import SeleniumDriver


class UndetectedChromeDriver(SeleniumDriver):
    """
    Anti-detection Chrome WebDriver backed by ``undetected-chromedriver``.

    Patches the ChromeDriver binary at runtime to bypass bot-detection
    systems such as Cloudflare, PerimeterX, and DataDome.

    Anti-detection measures applied at launch:

    - ``--disable-blink-features=AutomationControlled`` removes the
      ``navigator.webdriver`` flag at the Chrome level.
    - A realistic ``User-Agent`` string is injected via Chrome options.
    - Subprocess mode (``use_subprocess=True``) produces a more natural
      OS process tree that is harder to fingerprint.
    - ``navigator.webdriver``, ``navigator.languages``, and
      ``navigator.plugins`` are overridden via CDP to mimic a real user's
      browser environment.
    - Realistic window size (``1920×1080``) avoids headless-specific
      viewport signatures.
    - Optional Chrome version pin through
      ``Environment.SETTINGS.BROWSER.CHROME_VERSION`` ensures the correct
      driver binary is used when a specific Chrome version is installed.

    Inherits all network filtering capabilities from
    :class:`~SeleniumConnectPy.drivers.selenium.SeleniumDriver`:
    use :attr:`NETWORK_BLOCKED_EXTENSIONS` to block resources by file
    extension and :attr:`NETWORK_DOMAIN_WHITELIST` to restrict DNS
    resolution to specific domains.
    """

    _driver_type = "UndetectedChrome"
    DEFAULT_ARGUMENTS = (
        "--disable-blink-features=AutomationControlled", "--window-size=1920,1080",
        "--start-maximized", "--no-sandbox", "--disable-dev-shm-usage",
        "--disable-extensions", "--disable-infobars",
    )
    HEADLESS_ARGUMENT = "--headless=new"

    def __del__(self):
        self._browser.quit()

    def _launch_browser(self):
        """
        Instantiates a ``uc.Chrome`` (undetected-chromedriver) instance with
        stealth options, download preferences, and active network filters.

        Steps performed:

        1. Builds ``uc.ChromeOptions`` with stability, stealth arguments,
           and a realistic ``User-Agent``.
        2. Applies the domain whitelist via ``--host-rules`` if
           :attr:`NETWORK_DOMAIN_WHITELIST` is set.
        3. Configures automatic file downloads to
           :attr:`~SeleniumDriver.download_tmp_directory`.
        4. Resolves the Chrome version pin from
           ``Environment.SETTINGS.BROWSER.CHROME_VERSION`` (if set) and
           creates the ``uc.Chrome`` instance with ``use_subprocess=True``.
        5. Overrides ``navigator.webdriver``, ``navigator.languages``, and
           ``navigator.plugins`` via ``Page.addScriptToEvaluateOnNewDocument``
           to reduce the automation fingerprint.
        6. Applies extension-based request blocking via CDP
           (:meth:`~SeleniumDriver._setup_network_extension_filter`).
        """
        options = uc.ChromeOptions()

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

        params = {}
        if Environment.SETTINGS.BROWSER.CHROME_VERSION:
            params["version_main"] = Environment.SETTINGS.BROWSER.CHROME_VERSION
        self._browser = uc.Chrome(options=options, use_subprocess=True, **params)
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
