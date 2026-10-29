from __future__ import annotations

import logging
import os.path
import random
import time
from abc import ABC
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
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

    Provides shared browser configuration and lifecycle management, scraper
    execution, browser actions, network filtering, and utility methods. Concrete
    drivers implement :meth:`_launch_browser` and :meth:`_run`.

    Attributes:
        initial_url (str): Starting URL the browser will navigate to on launch.
        _download_directory (str): Path to the download directory.
        headless_browser (bool): Whether the browser runs in headless mode.
        wait_seconds (int): Timeout in seconds used for browser waits.
        _driver_type: Type of driver in use (Chrome, Firefox, etc.).
        _browser (WebDriver): Selenium WebDriver instance.
        _wait_driver (WebDriverWait): Selenium explicit wait instance.
        required_fields (list): Fields required by :meth:`run` and the
            subclass's :meth:`_run` implementation.
        custom_arguments (list[str]): Browser command-line arguments supplied
            by the caller.
        NETWORK_BLOCKED_EXTENSIONS (list[str]): File extensions blocked on
            supported Chromium browsers.
        NETWORK_DOMAIN_WHITELIST (list[str]): Domains allowed by Chromium host
            rules when a subclass applies them.
        DEFAULT_ARGUMENTS (tuple[str, ...]): Browser arguments supplied by a
            concrete driver before caller-provided arguments.

    Core methods:
        ``setup``, ``run``, and ``teardown_class`` manage browser and scraper
        lifecycle. Subclasses implement ``_launch_browser`` and ``_run``.

    Actions:
        ``go_to_url``, ``send_keys``, and ``click_element`` control browser
        navigation and page elements. Network filter methods configure
        Chromium request and host rules.

    Utilities:
        Argument helpers, download cleanup, random user-agent and delay
        helpers, logging, and representation support reusable driver code.
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
    DEFAULT_ARGUMENTS: tuple[str, ...] = ()
    DOWNLOAD_DIRECTORY_REQUIRED = True

    # ------------------------------------------------------------------ Core
    # Browser configuration, lifecycle, validation, and scraper execution.

    def __init__(
        self,
        browser: Optional[WebDriver] = None,
        headless_browser: bool = True,
        wait_seconds: int = 3,
        download_directory: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        custom_arguments: Optional[Iterable[str]] = None,
        user_agent: Optional[str] = None,
        locale: Optional[str] = None,
        languages: Optional[Iterable[str]] = None,
        timezone: Optional[str] = None,
    ) -> None:
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
            logger (logging.Logger, optional): Logger used for driver messages.
                Defaults to a logger named after this module.
            custom_arguments (Iterable[str], optional): Browser command-line
                arguments to add when the browser is launched. Each argument
                must be a non-empty string.
            user_agent (str, optional): User-Agent to send. When omitted the
                browser's own User-Agent is kept, which is the most coherent
                choice; use :meth:`get_random_user_agent` for a random one.
            locale (str, optional): Browser locale such as ``"es-ES"``.
                Also used to derive ``languages`` when those are not given.
            languages (Iterable[str], optional): Ordered ``Accept-Language`` /
                ``navigator.languages`` values. Defaults to the locale and its
                base language (``["es-ES", "es"]``) when ``locale`` is set.
            timezone (str, optional): IANA timezone id such as
                ``"Europe/Madrid"``. Applied through CDP on Chromium browsers.
        """
        if browser:
            self._browser = browser
        self.headless_browser = headless_browser
        self.wait_seconds = wait_seconds
        self._download_directory = self._download_directory or download_directory
        self.logger = logger if logger is not None else logging.getLogger("janusium")
        self.statistics = StatisticsSelenium()
        if isinstance(custom_arguments, str):
            raise TypeError("custom_arguments must be an iterable of argument strings, not a string")
        self.custom_arguments = list(custom_arguments or ())
        if any(not isinstance(argument, str) or not argument for argument in self.custom_arguments):
            raise ValueError("Browser arguments must be non-empty strings")
        for name, value in (("user_agent", user_agent), ("locale", locale), ("timezone", timezone)):
            if value is not None and (not isinstance(value, str) or not value):
                raise ValueError(f"{name} must be a non-empty string")
        if isinstance(languages, str):
            raise TypeError("languages must be an iterable of language strings, not a string")
        self.user_agent = user_agent
        self.locale = locale
        self.languages = list(languages or ())
        if any(not isinstance(language, str) or not language for language in self.languages):
            raise ValueError("languages must contain non-empty strings")
        self.timezone = timezone

    def add_argument(self, argument: str) -> SeleniumDriver:
        """Add a custom browser command-line argument before setup."""
        if not isinstance(argument, str) or not argument:
            raise ValueError("Browser arguments must be non-empty strings")
        self.custom_arguments.append(argument)
        return self

    def add_arguments(self, arguments: Iterable[str]) -> SeleniumDriver:
        """Add multiple custom browser command-line arguments."""
        if isinstance(arguments, str):
            raise TypeError("arguments must be an iterable of argument strings, not a string")
        for argument in arguments:
            self.add_argument(argument)
        return self

    def _iter_browser_arguments(self) -> Iterator[str]:
        """Yield driver defaults followed by caller-provided arguments."""
        yield from self.DEFAULT_ARGUMENTS
        yield from self.custom_arguments
        if self.headless_browser:
            yield self.HEADLESS_ARGUMENT

    HEADLESS_ARGUMENT = "--headless"

    def _resolved_languages(self) -> list[str]:
        """Return explicit languages, or ones derived from ``locale`` (``es-ES`` -> ``es-ES, es``)."""
        if self.languages:
            return list(self.languages)
        if self.locale:
            base_language = self.locale.split("-")[0]
            return [self.locale] if base_language == self.locale else [self.locale, base_language]
        return []

    def _iter_identity_arguments(self) -> Iterator[str]:
        """Yield Chromium arguments for the configured User-Agent, locale and languages."""
        if self.user_agent:
            yield f"--user-agent={self.user_agent}"
        if self.locale:
            yield f"--lang={self.locale}"
        languages = self._resolved_languages()
        if languages:
            yield f"--accept-lang={','.join(languages)}"

    def _apply_timezone(self) -> None:
        """Override the browser timezone through CDP when ``timezone`` is set (Chromium only)."""
        if not self.timezone:
            return
        if not hasattr(self._browser, "execute_cdp_cmd"):
            self.logger.warning("[Identity] Browser does not support CDP. Timezone override skipped.")
            return
        self._browser.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": self.timezone})

    def setup(self) -> SeleniumDriver:
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

    def _validate_setup(self) -> None:
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
        if self.DOWNLOAD_DIRECTORY_REQUIRED and not self._browser and not self.download_directory:
            raise Exception("Not 'download_directory' defined.")

    def _validate_fields(self, params: Mapping[str, Any]) -> None:
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

    def teardown_class(self) -> None:
        """
        Quits the browser and releases associated resources.

        Safe to call when no browser was ever launched (``setup`` not run) and
        safe to call more than once.
        """
        if self._browser is None:
            return
        try:
            self._browser.quit()
        finally:
            self._browser = None
            self._wait_driver = None

    def _launch_browser(self) -> None:
        """
        Launches and initializes the browser instance.

        Must be implemented by concrete subclasses (ChromeDriver, FirefoxDriver).

        Raises:
            NotImplementedError: If called directly on ``SeleniumDriver``.
        """
        raise NotImplementedError("SeleniumDriver isn't a valid driver class. Use ChromeDriver or FirefoxDriver classes")

    def run(self, raise_exceptions: bool = True, **params: Any) -> tuple[Any, Optional[Exception]]:
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
            self.logger.exception(
                "[%s] Error occurred while running scrapper",
                self.__class__.__name__,
            )
            exception_generated = e
        return scrapper_data, exception_generated

    def _run(self, **params: Any) -> Any:
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
    def browser(self) -> Optional[WebDriver]:
        """WebDriver: Active Selenium browser instance."""
        return self._browser

    @property
    def wait_driver(self) -> Optional[WebDriverWait]:
        """WebDriverWait: Explicit wait instance associated with the browser."""
        return self._wait_driver

    @property
    def download_directory(self) -> str:
        """
        str: Absolute path to the download directory.

        Raises:
            Exception: If ``_download_directory`` is not defined.
            Exception: If the specified path does not exist on the file system.
        """
        if not self._download_directory:
            raise Exception("Not 'download_directory' defined.")
        if self._download_directory and not os.path.exists(self._download_directory):
            raise Exception(f"Download directory '{self._download_directory}' doesn't exist.")
        return self._download_directory

    @property
    def download_tmp_directory(self) -> str:
        """str: Path to the temporary download directory (defaults to ``download_directory``)."""
        return self.download_directory

    # ----------------------------------------------------------------- Utils
    # Reusable helpers for files, user agents, delays, logging, and display.

    def clean_download_directory(self) -> None:
        """Removes all files in the temporary download directory, leaving subdirectories untouched."""
        for entry in Path(self.download_tmp_directory).iterdir():
            if entry.is_file() or entry.is_symlink():
                entry.unlink()

    def get_random_user_agent(self) -> str:
        user_agent = random.choice(_SELENIUM_USER_AGENTS)
        return user_agent

    def get_random_time(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> float:
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
        delay = self.get_random_time(min_seconds, max_seconds)
        self.logger.debug("Sleeping %.2fs to avoid detection...", delay)
        time.sleep(delay)

    def sleep(self, seconds: float) -> None:
        """
        Pauses execution for a specified number of seconds.

        Args:
            seconds (float): Time to sleep in seconds.
        """
        self.logger.debug("Sleeping for %.2fs...", seconds)
        time.sleep(seconds)

    def get_logger(self) -> logging.Logger:
        """
        Retrieves the logger configured for this driver.

        Returns:
            logging.Logger: The configured logger, or this module's logger.
        """
        return self.logger

    def __repr__(self) -> str:
        """
        Returns a string representation of the driver.

        Returns:
            str: String containing the class name, driver type, and initial URL.
        """
        return f"{self.__class__.__name__} (Driver: {self._driver_type}, Initial URL: {self.initial_url})"

    # --------------------------------------------------------------- Actions
    # Browser navigation, element interaction, and network configuration.

    def go_to_url(self, url: str, delay_seconds_added: Optional[float] = None) -> None:
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

    def send_keys(self, element: WebElement, value: str, use_script: bool = False) -> None:
        """Send text to an element, optionally setting its value through JavaScript.

        Script mode dispatches ``input`` and ``change`` events so that
        JavaScript frameworks detect the change.

        Args:
            element: The target input element.
            value: The text or value to enter.
            use_script (bool): If ``True``, set the value using JavaScript;
                otherwise call the element's ``send_keys`` method.
        """
        if not use_script:
            element.send_keys(value)
        else:
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

    def click_element(self, element: WebElement, use_script: bool = False) -> None:
        """Click an element normally or through a JavaScript click.

        Args:
            element: The DOM element to click.
            use_script (bool): If ``True``, dispatch a click through JavaScript;
                otherwise call the element's ``click`` method.
        """
        if not use_script:
            element.click()
        else:
            self.browser.execute_script("arguments[0].click();", element)

    def scroll_to_top(self) -> None:
        """Scroll the current page to the top."""
        self.browser.execute_script("window.scrollTo(0, 0);")

    def scroll_to(self, target: WebElement | int, y: Optional[int] = None) -> None:
        """Scroll to an element or to the given page coordinates.

        Args:
            target: Element to bring into view, or the horizontal coordinate
                when scrolling to a position.
            y: Vertical coordinate. Required when ``target`` is an ``x`` value.

        Raises:
            ValueError: If a horizontal coordinate is supplied without ``y``.
        """
        if isinstance(target, WebElement):
            self.browser.execute_script("arguments[0].scrollIntoView();", target)
            return
        if y is None:
            raise ValueError("The y coordinate is required when scrolling to coordinates")
        self.browser.execute_script("window.scrollTo(arguments[0], arguments[1]);", target, y)

    def scroll_to_bottom(self) -> None:
        """Scroll the current page to the bottom of its document."""
        self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def _setup_network_extension_filter(self) -> None:
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
            self.logger.warning("[NetworkFilter] Browser does not support CDP. Extension filter skipped.")
            return

        patterns = []
        for ext in self.NETWORK_BLOCKED_EXTENSIONS:
            ext = ext if ext.startswith(".") else f".{ext}"
            patterns.append(f"*{ext}")  # sin query string
            patterns.append(f"*{ext}?*")  # con query string / fragmento

        self._browser.execute_cdp_cmd("Network.enable", {})
        self._browser.execute_cdp_cmd("Network.setBlockedURLs", {"urls": patterns})
        self.logger.info(
            "[NetworkFilter] Blocked extensions: %s → %d URL patterns registered.",
            self.NETWORK_BLOCKED_EXTENSIONS,
            len(patterns),
        )

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
        self.logger.info("[NetworkFilter] Blocked extensions cleared.")

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
        self.logger.info("[NetworkFilter] Domain whitelist active: %s", self.NETWORK_DOMAIN_WHITELIST)
        return host_rules
