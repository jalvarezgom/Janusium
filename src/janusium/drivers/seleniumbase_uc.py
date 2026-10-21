from typing import Optional

from seleniumbase import Driver

from environment import Environment
from src.libs.SeleniumConnectPy.drivers.selenium import SeleniumDriver


class SeleniumBaseUCDriver(SeleniumDriver):
    """Chrome WebDriver managed by SeleniumBase in UC mode.

    This driver extends :class:`SeleniumDriver` and creates its browser with
    ``seleniumbase.Driver(uc=True)``. It inherits the shared setup, navigation,
    wait, statistics, and network-filtering behavior from the base class.

    Browser launch configuration includes headless mode, a randomly selected
    user-agent from the base class, a 1920x1080 window, and UC subprocess mode.
    If configured, the Chrome version pin from
    ``Environment.SETTINGS.BROWSER.CHROME_VERSION``, the domain whitelist,
    proxy, and download directory are also applied. Extension-based network
    filtering is activated after launch when configured.

    Args:
        browser (WebDriver, optional): Existing browser instance to reuse. When
            provided, SeleniumBase does not launch a new browser.
        headless_browser (bool): Run Chrome without a visible window. Defaults
            to ``True``.
        wait_seconds (int): Implicit and explicit wait timeout in seconds.
            Defaults to ``3``.
        download_directory (str, optional): Existing directory used for browser
            downloads.
        logger (logging.Logger, optional): Logger passed to
            :class:`SeleniumDriver`.
        proxy (str, optional): Proxy passed to SeleniumBase. Supported formats
            include ``HOST:PORT`` and ``USER:PASSWORD@HOST:PORT``.

    Example::

        driver = SeleniumBaseUCDriver(
            headless_browser=False,
            download_directory="C:/downloads",
            proxy="user:password@proxy.example.com:8080",
        )
        driver.setup()
        try:
            driver.go_to_url("https://example.com")
        finally:
            driver.browser.quit()
    """

    _driver_type = "SeleniumBaseUC"
    DOWNLOAD_DIRECTORY_REQUIRED = False

    def __init__(
        self,
        browser=None,
        headless_browser: bool = True,
        wait_seconds: int = 3,
        download_directory: Optional[str] = None,
        logger=None,
        proxy: Optional[str] = None,
        custom_arguments=None,
    ):
        """Initialize inherited Selenium settings and optional proxy config.

        Args:
            browser: Existing Selenium WebDriver instance to reuse.
            headless_browser: Whether Chrome runs without a visible window.
            wait_seconds: Timeout, in seconds, for Selenium waits.
            download_directory: Existing directory for downloaded files.
            logger: Optional logger forwarded to :class:`SeleniumDriver`.
            proxy: Optional SeleniumBase proxy in ``HOST:PORT`` or
                ``USER:PASSWORD@HOST:PORT`` format. It is only used when this
                class launches a new browser.

        Returns:
            None.
        """
        super().__init__(
            browser=browser,
            headless_browser=headless_browser,
            wait_seconds=wait_seconds,
            download_directory=download_directory,
            logger=logger,
            custom_arguments=custom_arguments,
        )
        self.proxy = proxy
        self._owns_browser = browser is None

    def __del__(self):
        browser = getattr(self, "_browser", None)
        if browser and getattr(self, "_owns_browser", False):
            browser.quit()

    def _launch_browser(self):
        """Launch SeleniumBase UC with this instance's browser settings.

        Applies headless mode, user-agent, window size, and subprocess mode;
        adds configured host resolver rules, Chrome version, and proxy; then
        configures the download directory and inherited network extension
        filters when those options are set.
        """
        options = {
            "uc": True,
            "headless": self.headless_browser,
            "agent": self.get_random_user_agent(),
            "window_size": "1920,1080",
            "uc_subprocess": True,
        }
        arguments = list(self._iter_browser_arguments())
        if arguments:
            options["chromium_arg"] = ",".join(argument.removeprefix("--") for argument in arguments)

        host_rules = self._build_host_rules_argument()
        if host_rules:
            options["host_resolver_rules"] = host_rules

        chrome_version = Environment.SETTINGS.BROWSER.CHROME_VERSION
        if chrome_version:
            options["driver_version"] = str(chrome_version)
        if self.proxy:
            options["proxy"] = self.proxy

        self._browser = Driver(**options)

        if self._download_directory:
            download_directory = self.download_directory
            self._browser.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": download_directory},
            )

        self._setup_network_extension_filter()
