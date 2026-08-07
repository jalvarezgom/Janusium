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
        :class:`~SeleniumConnectPy.drivers.selenium.SeleniumDriver`
        (:attr:`NETWORK_BLOCKED_EXTENSIONS`, :attr:`NETWORK_DOMAIN_WHITELIST`)
        are silently skipped when using this driver.
    """

    _driver_type = "Firefox"
    use_service = False

    def __init__(self, executable_path=None, log_path=None, service_args=None, **base_options):
        """
        Initializes the Firefox driver with optional GeckoDriver service
        parameters.

        Args:
            executable_path (str, optional): Absolute path to the
                ``geckodriver`` binary.  When omitted, Selenium resolves
                the binary from the system ``PATH``.
            log_path (str, optional): Path to the GeckoDriver log file.
            service_args (list[str], optional): Additional arguments passed
                to the GeckoDriver service process.
            **base_options: Forwarded to :meth:`SeleniumDriver.__init__`
                (e.g. ``headless_browser``, ``wait_seconds``,
                ``download_directory``, ``logger``).
        """
        super().__init__(**base_options)
        self.executable_path = executable_path
        self.log_path = log_path
        self.service_args = service_args

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
        download_directory = self.download_directory.replace("/", "\\")
        options = Options()
        # options.set_preference("browser.privatebrowsing.autostart", True)
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.download.dir", rf"{download_directory}")
        options.set_preference("browser.helperApps.neverAsk.openFile", "text/csv,application/vnd.ms-excel;application/xls")
        options.set_preference(
            "browser.helperApps.neverAsk.saveToDisk",
            "text/csv,application/vnd.ms-excel,application/xls,"
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
            "application/vnd.openxmlformats-officedocument.spreadsheetml.template,"
            "application/vnd.ms-excel.sheet.macroEnabled.12,"
            "application/vnd.ms-excel.template.macroEnabled.12,"
            "application/vnd.ms-excel.addin.macroEnabled.12,"
            "application/vnd.ms-excel.sheet.binary.macroEnabled.12",
        )
        options.set_preference("pdfjs.disabled", True)
        if self.headless_browser:
            options.add_argument("--headless")
        # Related: https://stackoverflow.com/questions/66597600/how-to-connect-to-standalone-selenium-firefox-container-from-another-container
        if self.executable_path:
            service = FirefoxService(executable_path=self.executable_path, log_path=self.log_path, service_args=self.service_args)
            self._browser = webdriver.Firefox(service=service, options=options)
        else:
            self._browser = webdriver.Firefox(options=options)
