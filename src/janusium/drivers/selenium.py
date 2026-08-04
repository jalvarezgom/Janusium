import logging
import os.path
import random
import time
from abc import ABC
from pathlib import Path
from typing import Any, Mapping, Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait

from janusium.statistics import StatisticsSelenium

_SELENIUM_USER_AGENTS = [
    # Chrome - Windows 10
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    # Chrome - Windows 11
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.76 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.57 Safari/537.36",
    # Chrome - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    # Chrome - Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


class SeleniumDriver(ABC):
    """
    Abstract base class for Selenium drivers.

    Defines the interface and shared logic for initializing, configuring, and
    operating web browsers through Selenium WebDriver.

    Attributes:
        initial_url (str): Starting URL the browser will navigate to on launch.
        _download_directory (str): Path to the download directory.
        headless_browser (bool): Whether the browser runs in headless mode.
        wait_seconds (int): Maximum implicit wait time in seconds.
        _driver_type: Type of driver in use (Chrome, Firefox, etc.).
        _browser (WebDriver): Selenium WebDriver instance.
        _wait_driver (WebDriverWait): Selenium explicit wait instance.
        required_fields (list): List of mandatory fields required for execution.
    """

    initial_url = None
    _download_directory = None
    headless_browser = True
    wait_seconds = 3
    _driver_type = None
    _browser: WebDriver = None
    _wait_driver: WebDriverWait = None

    # [Others]
    required_fields = []

    # [NETWORK]
    NETWORK_BLOCKED_EXTENSIONS: list[str] = []  # e.g. [".jpg", ".png", ".css", ".woff2"].
    NETWORK_DOMAIN_WHITELIST: list[str] = []

    def __init__(
        self,
        browser: Optional[WebDriver] = None,
        headless_browser: bool = True,
        wait_seconds: int = 3,
        download_directory: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initializes the driver with basic browser options.

        Args:
            browser (WebDriver, optional): An already-instantiated WebDriver to
                reuse instead of launching a new one.  When provided,
                ``_launch_browser`` is skipped during ``setup``.
            headless_browser (bool): If ``True``, the browser runs without a
                graphical interface.  Defaults to ``True``.
            wait_seconds (int): Implicit wait time in seconds for locating DOM
                elements.  Defaults to ``3``.
            download_directory (str, optional): Absolute path to the directory
                where downloaded files will be stored.
            logger (logging.Logger, optional): Logger instance for recording
                messages.  If not provided, a default logger is created using
                the module name.
        """
        if browser:
            self._browser = browser
        self.headless_browser = headless_browser
        self.wait_seconds = wait_seconds
        self._download_directory = self._download_directory or download_directory
        self.logger = logger or logging.getLogger(__name__)
        self.statistics = StatisticsSelenium()

    def setup(self):
        """
        Configures and initializes the browser.

        Validates configuration parameters, launches the browser, sets up wait
        times, and navigates to ``initial_url``.

        Returns:
            SeleniumDriver: The current instance to allow method chaining.

        Raises:
            Exception: If ``_driver_type`` is ``None``, ``wait_seconds`` is not
                valid, or ``initial_url`` is not defined.
        """
        self._validate_setup()
        if not self._browser:
            self._launch_browser()
            self.browser.implicitly_wait(self.wait_seconds)
            self.browser.get(self.initial_url)
        self._wait_driver = WebDriverWait(self.browser, self.wait_seconds)
        return self

    def _validate_setup(self):
        """
        Validates that the minimum required attributes are correctly defined.

        Raises:
            Exception: If ``_driver_type`` is ``None``.
            Exception: If ``wait_seconds`` is not a valid integer.
            Exception: If ``initial_url`` is not defined.
        """
        if self._driver_type is None:
            raise Exception(f"{self.__class__.__name__} isn't a valid driver class. Use ChromeDriver or FirefoxDriver classes.")
        if not self.wait_seconds or not isinstance(self.wait_seconds, int):
            raise Exception(f"Variable 'wait_seconds' is not valid value - value:{self.wait_seconds}.")
        if not self.initial_url:
            raise Exception("Not 'initial_url' defined.")

    def _validate_fields(self, params: Mapping[str, Any]):
        """
        Validates that all required fields are present in ``params``.

        Args:
            params (dict): Dictionary of parameters to validate.

        Raises:
            Exception: If any field defined in ``required_fields`` is missing
                from ``params``.
        """
        for field in self.required_fields:
            if field not in params:
                raise Exception(f"Field {field} is required")

    def teardown_class(self):
        """Closes the browser and releases associated resources."""
        self.browser.close()

    def _launch_browser(self):
        """
        Launches and initializes the browser instance.

        Must be implemented by concrete subclasses (ChromeDriver, FirefoxDriver).

        Raises:
            NotImplementedError: If called directly on ``SeleniumDriver``.
        """
        raise NotImplementedError("SeleniumDriver isn't a valid driver class. Use ChromeDriver or FirefoxDriver classes")

    def run(self, raise_exceptions: bool = True, **params: Any):
        """
        Executes the main scraping logic defined in :meth:`_run`.

        Validates required fields before delegating to ``_run``.  If
        ``raise_exceptions`` is ``False``, any exception is swallowed,
        logged at *error* level, and returned as the second element of the
        result tuple instead of being re-raised.

        Args:
            raise_exceptions (bool): If ``True`` (default), exceptions
                propagate to the caller.  If ``False``, they are caught and
                returned together with ``None`` data.
            **params: Arbitrary keyword arguments forwarded to ``_run``.

        Returns:
            tuple[Any, Exception | None]: A ``(data, exception)`` pair where
            ``data`` is whatever ``_run`` returns and ``exception`` is ``None``
            on success or the caught exception on failure.

        Raises:
            Exception: Any exception raised by ``_run`` when
                ``raise_exceptions`` is ``True``.
        """
        scrapper_data, exception_generated = None, None
        try:
            self._validate_fields(params)
            self.statistics.start_timer()
            scrapper_data = self._run(**params)
            self.statistics.end_timer()
        except Exception as e:
            if raise_exceptions:
                raise e
            self.logger.error(f"[{self.__class__.__name__}] Error occurred while running scrapper: {e}")
            exception_generated = e
        return scrapper_data, exception_generated

    def _run(self, **params: Any):
        """
        Contains the core scraping logic.

        Must be implemented by concrete subclasses.

        Args:
            **params: Implementation-specific parameters.

        Raises:
            NotImplementedError: If not implemented in the subclass.
        """
        raise NotImplementedError("Method _run must be implemented")

    @property
    def browser(self):
        """WebDriver: Active Selenium browser instance."""
        return self._browser

    @property
    def wait_driver(self):
        """WebDriverWait: Explicit wait instance associated with the browser."""
        return self._wait_driver

    @property
    def download_directory(self):
        """
        str: Absolute path to the download directory.

        Raises:
            Exception: If ``_download_directory`` is not defined.
            Exception: If the specified path does not exist on the file system.
        """
        if self._download_directory and not os.path.exists(self._download_directory):
            raise Exception(f"Download directory '{self._download_directory}' doesn't exist.")
        return self._download_directory

    @property
    def download_tmp_directory(self):
        """str: Path to the temporary download directory (defaults to ``download_directory``)."""
        return self.download_directory

    def clean_download_directory(self):
        """Removes all files present in the temporary download directory."""
        download_path = Path(self.download_tmp_directory)
        if any(download_path.iterdir()):
            for file in download_path.iterdir():
                file.unlink()

    def get_random_user_agent(self):
        user_agent = random.choice(_SELENIUM_USER_AGENTS)
        return user_agent

    def get_random_sleep_time(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> float:
        """
        Generates a random sleep time between the specified minimum and maximum.

        Args:
            min_seconds (float): Minimum sleep time in seconds.  Defaults to ``1.0``.
            max_seconds (float): Maximum sleep time in seconds.  Defaults to ``3.0``.

        Returns:
            float: A random float value within ``[min_seconds, max_seconds]``.
        """
        return random.uniform(min_seconds, max_seconds)

    def random_sleep(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """
        Pauses execution for a random interval of time.

        Simulates human-like behaviour to reduce the likelihood of bot detection.

        Args:
            min_seconds (float): Minimum wait time in seconds. Defaults to ``1.0``.
            max_seconds (float): Maximum wait time in seconds. Defaults to ``3.0``.
        """
        delay = self.get_random_sleep_time(min_seconds, max_seconds)
        self.get_logger().debug(f"Sleeping {delay:.2f}s to avoid detection...")
        time.sleep(delay)

    def sleep(self, seconds: float) -> None:
        """
        Pauses execution for a specified number of seconds.

        Args:
            seconds (float): Time to sleep in seconds.
        """
        self.get_logger().debug(f"Sleeping for {seconds:.2f}s...")
        time.sleep(seconds)

    def go_to_url(self, url: str, delay_seconds_added: float = None) -> None:
        """
        Navigates the browser to the given URL and records the request in the
        statistics tracker.

        Args:
            url (str): The target URL to navigate to.
            delay_seconds_added (float, optional): Extra seconds to wait
                *before* navigating, on top of any implicit wait already
                configured.  Useful for adding human-like pauses between
                page loads.  Defaults to ``None`` (no extra delay).
        """
        if delay_seconds_added:
            self.sleep(delay_seconds_added)
        self.statistics.add_request()
        self.browser.get(url)

    def send_keys_script(self, element, value) -> None:
        """
        Sets the value of a form input element via JavaScript and dispatches
        the ``input`` and ``change`` events so that React / Vue / Angular
        frameworks detect the change correctly.

        This is useful when :meth:`element.send_keys` is blocked or intercepted
        by the page's JavaScript framework.

        Args:
            element (WebElement): The target ``<input>`` DOM element.
            value (str): The value to assign to the element.
        """
        self.browser.execute_script(
            """
            const element = arguments[0];
            const value = arguments[1];
            const valueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            valueSetter.call(element, value);
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            element,
            value,
        )

    def click_element_script(self, element) -> None:
        """
        Clicks a DOM element by dispatching a programmatic JavaScript click.

        Use this method when the standard
        :meth:`~selenium.webdriver.remote.webelement.WebElement.click` is
        intercepted or blocked by an overlay element.

        Args:
            element (WebElement): The DOM element to click.
        """
        self.browser.execute_script("arguments[0].click();", element)

    def get_logger(self):
        """
        Retrieves the logger configured for the scraper.

        Returns:
            logging.Logger: Logger instance named ``'scrapper'``.
        """
        return logging.getLogger("scrapper")

    def __repr__(self):
        """
        Returns a string representation of the driver.

        Returns:
            str: String containing the class name, driver type, and initial URL.
        """
        return f"{self.__class__.__name__} (Driver: {self._driver_type}, Initial URL: {self.initial_url})"

    def _setup_network_extension_filter(self):
        """
        Registers CDP ``Network.setBlockedURLs`` patterns derived from
        :attr:`NETWORK_BLOCKED_EXTENSIONS` so that Chrome aborts matching
        network requests before they are sent.

        Two glob patterns are registered per extension:

        - ``*<ext>``   – matches URLs without a query string.
        - ``*<ext>?*`` – matches URLs that include a query string or fragment.

        This method is a no-op when :attr:`NETWORK_BLOCKED_EXTENSIONS` is
        empty.  If the active browser does not expose ``execute_cdp_cmd``
        (e.g. Firefox), a warning is logged and the method returns silently.

        Example extensions: ``".jpg"``, ``".png"``, ``".css"``, ``".woff2"``,
        ``".svg"``, ``".ico"``, ``".ttf"``, ``".mp4"``, ``".webp"``.
        """
        if not self.NETWORK_BLOCKED_EXTENSIONS:
            return

        if not hasattr(self._browser, "execute_cdp_cmd"):
            self.get_logger().warning("[NetworkFilter] Browser does not support CDP. Extension filter skipped.")
            return

        patterns = []
        for ext in self.NETWORK_BLOCKED_EXTENSIONS:
            ext = ext if ext.startswith(".") else f".{ext}"
            patterns.append(f"*{ext}")  # sin query string
            patterns.append(f"*{ext}?*")  # con query string / fragmento

        self._browser.execute_cdp_cmd("Network.enable", {})
        self._browser.execute_cdp_cmd("Network.setBlockedURLs", {"urls": patterns})
        self.get_logger().info(f"[NetworkFilter] Blocked extensions: {self.NETWORK_BLOCKED_EXTENSIONS} → {len(patterns)} URL patterns registered.")

    def set_blocked_extensions(self, *extensions: str) -> None:
        """
        Updates the list of blocked file extensions at runtime and immediately
        applies the new filter to the already-running browser.

        Only effective on Chromium-based drivers (requires CDP).

        Args:
            *extensions (str): File extensions to block, with or without a
                leading dot (e.g. ``".jpg"`` or ``"jpg"``).

        Example::

            driver.set_blocked_extensions(".jpg", ".png", ".css", ".woff2")
        """
        self.NETWORK_BLOCKED_EXTENSIONS = list(extensions)
        self._setup_network_extension_filter()

    def clear_blocked_extensions(self) -> None:
        """
        Removes all active extension-based network filters.

        Resets :attr:`NETWORK_BLOCKED_EXTENSIONS` to an empty list and, if the
        browser supports CDP, sends an empty ``Network.setBlockedURLs`` command
        to lift all previously registered URL blocks.
        """
        self.NETWORK_BLOCKED_EXTENSIONS = []
        if hasattr(self._browser, "execute_cdp_cmd"):
            self._browser.execute_cdp_cmd("Network.setBlockedURLs", {"urls": []})
        self.get_logger().info("[NetworkFilter] Blocked extensions cleared.")

    def _build_host_rules_argument(self) -> Optional[str]:
        """
        Builds the value for Chrome's ``--host-rules`` command-line flag based
        on :attr:`NETWORK_DOMAIN_WHITELIST`.

        The generated rule maps all hostnames to ``~NOTFOUND`` (DNS block) and
        then explicitly excludes each domain in the whitelist, effectively
        allowing only those domains to resolve.

        Returns ``None`` when :attr:`NETWORK_DOMAIN_WHITELIST` is empty so
        that callers can use a simple ``if`` / walrus-operator guard:

        .. code-block:: python

            if host_rules := self._build_host_rules_argument():
                options.add_argument(f"--host-rules={host_rules}")

        .. note::
            This argument is Chrome/Chromium-specific.  Firefox drivers must
            not call this method.

        Returns:
            str | None: The ``--host-rules`` value string, or ``None`` if no
            whitelist is configured.
        """
        if not self.NETWORK_DOMAIN_WHITELIST:
            return None
        excludes = ", ".join(f"EXCLUDE {domain}" for domain in self.NETWORK_DOMAIN_WHITELIST)
        host_rules = f"MAP * ~NOTFOUND, {excludes}"
        self.get_logger().info(f"[NetworkFilter] Domain whitelist active: {self.NETWORK_DOMAIN_WHITELIST}")
        return host_rules
