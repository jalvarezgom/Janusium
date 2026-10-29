import os
from typing import Any, Iterable, Optional

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from janusium.drivers.selenium import SeleniumDriver
from selenium.webdriver.firefox.service import Service as FirefoxService


class FirefoxDriver(SeleniumDriver):
    """
    Mozilla Firefox WebDriver.

    Wraps ``selenium.webdriver.Firefox`` and configures GeckoDriver for
    automatic file downloads without user prompts.

    Supported file types saved silently: CSV, XLS, XLSX, XLSM, XLSB, XLTX,
    XLTM, XLAM (and their MIME-type equivalents).

    .. note::
        Firefox does not support the Chrome DevTools Protocol (CDP).
        Network filtering features inherited from
        :class:`~janusium.drivers.selenium.SeleniumDriver`
        (:attr:`NETWORK_BLOCKED_EXTENSIONS`, :attr:`NETWORK_DOMAIN_WHITELIST`)
        are silently skipped when using this driver.
    """

    _driver_type = "Firefox"
    use_service = False
    DEFAULT_ARGUMENTS = ()
    HEADLESS_ARGUMENT = "--headless"
    DEFAULT_PREFERENCES = (
        ("browser.download.folderList", 2),
        ("browser.download.manager.showWhenStarting", False),
        ("browser.helperApps.neverAsk.openFile", "text/csv,application/vnd.ms-excel;application/xls"),
        (
            "browser.helperApps.neverAsk.saveToDisk",
            "text/csv,application/vnd.ms-excel,application/xls,"
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
            "application/vnd.openxmlformats-officedocument.spreadsheetml.template,"
            "application/vnd.ms-excel.sheet.macroEnabled.12,"
            "application/vnd.ms-excel.template.macroEnabled.12,"
            "application/vnd.ms-excel.addin.macroEnabled.12,"
            "application/vnd.ms-excel.sheet.binary.macroEnabled.12",
        ),
        ("pdfjs.disabled", True),
    )

    def __init__(
        self,
        executable_path: Optional[str] = None,
        log_path: Optional[str] = None,
        service_args: Optional[list[str]] = None,
        custom_preferences: Optional[Iterable[tuple[str, Any]]] = None,
        **kwargs: Any,
    ):
        """
        Initializes the Firefox driver with optional GeckoDriver service
        parameters.

        Args:
            executable_path (str, optional): Absolute path to the
                ``geckodriver`` binary.  When omitted, Selenium resolves the
                binary from the system ``PATH``.
            log_path (str, optional): Path to the GeckoDriver log file.
            service_args (list[str], optional): Additional arguments passed
                to the GeckoDriver service process.
            custom_preferences (Iterable[tuple[str, Any]], optional): Extra
                Firefox ``(name, value)`` preferences applied on launch.
            **kwargs: Forwarded to :class:`SeleniumDriver` (``browser``,
                ``headless_browser``, ``wait_seconds``, ``download_directory``,
                ``logger``, ``custom_arguments``). Unknown options raise
                ``TypeError``.
        """
        self.executable_path = executable_path
        self.log_path = log_path
        self.service_args = service_args
        self.custom_preferences = list(custom_preferences or ())
        super().__init__(**kwargs)

    def add_argument(self, name: str, value):
        """Add a Firefox preference; browser CLI arguments are handled internally."""
        if not isinstance(name, str) or not name:
            raise ValueError("Firefox preference names must be non-empty strings")
        self.custom_preferences.append((name, value))
        return self

    add_preference = add_argument

    def _iter_browser_arguments(self):
        """Yield only Firefox CLI arguments managed by this driver (headless)."""
        if self.headless_browser:
            yield self.HEADLESS_ARGUMENT

    def _iter_preferences(self):
        yield from self.DEFAULT_PREFERENCES
        yield from self.custom_preferences
        if self.user_agent:
            yield ("general.useragent.override", self.user_agent)
        languages = self._resolved_languages()
        if languages:
            yield ("intl.accept_languages", ",".join(languages))

    def setup(self):
        """
        Configures and initializes the Firefox browser.

        Delegates to the parent :meth:`SeleniumDriver.setup` and returns
        ``self`` to support method chaining.

        Returns:
            FirefoxDriver: The current instance.
        """
        super().setup()
        return self

    def _launch_browser(self):
        """
        Instantiates a ``selenium.webdriver.Firefox`` instance with download
        preferences pre-configured for silent file saving.

        Steps performed:

        1. Sets Firefox preferences so that CSV and Excel files are saved
           automatically to :attr:`~SeleniumDriver.download_directory`
           without showing the download manager or prompting the user.
        2. Disables the built-in PDF viewer (``pdfjs``) to prevent PDFs from
           being opened in-browser.
        3. Applies ``--headless`` mode if :attr:`headless_browser` is
           ``True``.
        4. If ``executable_path`` was provided to ``__init__``, creates a
           :class:`~selenium.webdriver.firefox.service.Service` with the
           supplied parameters; otherwise relies on the system ``PATH``.
        """
        download_directory = os.path.normpath(self.download_directory)
        options = Options()
        # options.set_preference("browser.privatebrowsing.autostart", True)
        if self.timezone:
            self.logger.warning("[Identity] Firefox does not support CDP. Timezone override skipped.")
        for name, value in self._iter_preferences():
            options.set_preference(name, value)
        options.set_preference("browser.download.dir", rf"{download_directory}")
        for argument in self._iter_browser_arguments():
            options.add_argument(argument)
        # Related: https://stackoverflow.com/questions/66597600/how-to-connect-to-standalone-selenium-firefox-container-from-another-container
        if self.executable_path:
            service = FirefoxService(executable_path=self.executable_path, log_path=self.log_path, service_args=self.service_args)
            self._browser = webdriver.Firefox(service=service, options=options)
        else:
            self._browser = webdriver.Firefox(options=options)
