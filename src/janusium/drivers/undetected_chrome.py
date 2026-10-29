import os

try:
    import undetected_chromedriver as uc
except ImportError as exc:
    raise ImportError(
        "undetected-chromedriver is required for this driver. Install it with: pip install janusium[undetected]"
    ) from exc

from janusium.drivers.selenium import SeleniumDriver


class UndetectedChromeDriver(SeleniumDriver):
    """
    Anti-detection Chrome WebDriver backed by ``undetected-chromedriver``.

    Patches the ChromeDriver binary at runtime to bypass bot-detection
    systems such as Cloudflare, PerimeterX, and DataDome.

    Anti-detection measures applied at launch:

    - ``--disable-blink-features=AutomationControlled`` removes the
      ``navigator.webdriver`` flag at the Chrome level.
    - The browser's own ``User-Agent`` is kept unless ``user_agent`` is given.
    - Subprocess mode (``use_subprocess=True``) produces a more natural
      OS process tree that is harder to fingerprint.
    - ``locale``, ``languages`` and ``timezone`` are applied through native
      Chrome switches / CDP instead of patching ``navigator`` from JavaScript.
    - Realistic window size (``1920×1080``) avoids headless-specific
      viewport signatures.
    - Optional Chrome version pin through
      ``chrome_version`` ensures the correct
      driver binary is used when a specific Chrome version is installed.

    Inherits all network filtering capabilities from
    :class:`~janusium.drivers.selenium.SeleniumDriver`:
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

    def __init__(self, *args, chrome_version=None, **kwargs):
        """
        Args:
            chrome_version (int, optional): Chrome major version to pin the
                driver binary to.
            *args, **kwargs: Forwarded to :class:`SeleniumDriver`.
        """
        super().__init__(*args, **kwargs)
        self.chrome_version = chrome_version
        self._owns_browser = self._browser is None

    def __del__(self):
        # Only quit browsers launched by this instance, and only if one exists.
        browser = getattr(self, "_browser", None)
        if browser and getattr(self, "_owns_browser", False):
            browser.quit()

    def _launch_browser(self):
        """
        Instantiates a ``uc.Chrome`` (undetected-chromedriver) instance with
        stealth options, download preferences, and active network filters.

        Steps performed:

        1. Builds ``uc.ChromeOptions`` with stability, stealth arguments,
           and the optional ``user_agent`` / ``locale`` / ``languages``.
        2. Applies the domain whitelist via ``--host-rules`` if
           :attr:`NETWORK_DOMAIN_WHITELIST` is set.
        3. Configures automatic file downloads to
           :attr:`~SeleniumDriver.download_tmp_directory`.
        4. Resolves the Chrome version pin from
           ``chrome_version`` (if set) and
           creates the ``uc.Chrome`` instance with ``use_subprocess=True``.
        5. Applies extension-based request blocking via CDP
           (:meth:`~SeleniumDriver._setup_network_extension_filter`).
        6. Applies the optional ``timezone`` override via CDP.
        """
        options = uc.ChromeOptions()

        for argument in (*self._iter_browser_arguments(), *self._iter_identity_arguments()):
            options.add_argument(argument)
        host_rules = self._build_host_rules_argument()
        if host_rules:
            options.add_argument(f"--host-rules={host_rules}")

        download_directory = os.path.normpath(self.download_tmp_directory)
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
        if self.chrome_version:
            params["version_main"] = self.chrome_version
        self._browser = uc.Chrome(options=options, use_subprocess=True, **params)
        self._setup_network_extension_filter()
        self._apply_timezone()
