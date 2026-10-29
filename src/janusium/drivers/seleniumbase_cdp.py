from __future__ import annotations

import json
import random
import time
from typing import Any, Optional

try:
    import mycdp as cdp
    from seleniumbase import sb_cdp
except ImportError as exc:
    raise ImportError(
        "seleniumbase is required for this driver. Install it with: pip install janusium[seleniumbase]"
    ) from exc

from janusium import humanize
from janusium.drivers.selenium import SeleniumDriver


class SeleniumBaseCDPDriver(SeleniumDriver):
    """Chrome controlled directly through the DevTools Protocol (SeleniumBase CDP Mode).

    The browser is started with ``seleniumbase.sb_cdp.Chrome``: there is no
    chromedriver and no WebDriver session, which leaves far fewer automation
    traces than :class:`~janusium.drivers.seleniumbase_uc.SeleniumBaseUCDriver`.

    Because there is no Selenium ``WebDriver``, this driver inherits the
    lifecycle, statistics, argument handling and utilities of
    :class:`~janusium.drivers.selenium.SeleniumDriver`, but its actions take
    **selector strings** (CSS, or XPath starting with ``/`` or ``(``) instead of
    ``WebElement`` objects. The underlying
    SeleniumBase CDP object is available as :attr:`cdp` for anything not wrapped
    here (``driver.cdp.get_text("h1")``, ``driver.cdp.evaluate(...)``, ...).

    Locale, languages, timezone, user-agent, proxy and the domain whitelist are
    applied when the browser launches. ``chrome_version`` does not apply.

    Human-like input (``human=True``) is replayed as CDP ``Input`` events, so it
    works in headless mode and does not move the operating-system cursor.

    Args:
        headless_browser (bool): Run Chrome without a visible window. Defaults
            to ``True``. CDP Mode is harder to detect with a visible window.
        wait_seconds (int): Timeout, in seconds, for element lookups.
        download_directory (str, optional): Existing directory for downloads.
        logger (logging.Logger, optional): Logger passed to
            :class:`SeleniumDriver`.
        proxy (str, optional): Proxy in ``HOST:PORT`` or
            ``USER:PASSWORD@HOST:PORT`` format.

    Example::

        class Scraper(SeleniumBaseCDPDriver):
            initial_url = "https://example.com"

            def _run(self, **params):
                self.click_element("a", human=True)
                return self.cdp.get_title()

        driver = Scraper(headless_browser=False).setup()
        try:
            data, error = driver.run()
        finally:
            driver.teardown_class()
    """

    _driver_type = "SeleniumBaseCDP"
    DOWNLOAD_DIRECTORY_REQUIRED = False

    def __init__(
        self,
        headless_browser: bool = True,
        wait_seconds: int = 3,
        download_directory: Optional[str] = None,
        logger=None,
        proxy: Optional[str] = None,
        custom_arguments=None,
        user_agent: Optional[str] = None,
        locale: Optional[str] = None,
        languages=None,
        timezone: Optional[str] = None,
    ):
        super().__init__(
            headless_browser=headless_browser,
            wait_seconds=wait_seconds,
            download_directory=download_directory,
            logger=logger,
            custom_arguments=custom_arguments,
            user_agent=user_agent,
            locale=locale,
            languages=languages,
            timezone=timezone,
        )
        self.proxy = proxy

    def __del__(self):
        if getattr(self, "_browser", None) is not None:
            try:
                self.teardown_class()
            except Exception:
                pass

    # ------------------------------------------------------------------ Core

    @property
    def cdp(self) -> Optional[sb_cdp.Chrome]:
        """sb_cdp.Chrome: SeleniumBase CDP Mode object controlling the browser."""
        return self._browser

    def setup(self) -> SeleniumBaseCDPDriver:
        """Validate the configuration and launch the browser on ``initial_url``."""
        self._validate_setup()
        if not self._browser:
            self._launch_browser()
        return self

    def _launch_browser(self) -> None:
        """Start Chrome in CDP Mode with this instance's settings.

        Headless mode, proxy, user-agent, locale and timezone use native
        SeleniumBase options; the remaining arguments, the accepted languages
        and the domain whitelist are passed as Chromium arguments. The download
        directory and extension-based network filter are applied once the
        browser is up; with a filter, ``initial_url`` is opened only after it
        is registered so the first page is filtered too.
        """
        arguments = [*self.DEFAULT_ARGUMENTS, *self.custom_arguments]
        languages = self._resolved_languages()
        if languages:
            arguments.append(f"--accept-lang={','.join(languages)}")
        host_rules = self._build_host_rules_argument()
        if host_rules:
            arguments.append(f"--host-rules={host_rules}")

        options: dict[str, Any] = {"headless": self.headless_browser}
        if arguments:
            options["browser_args"] = arguments
        if self.user_agent:
            options["agent"] = self.user_agent
        if self.locale:
            options["lang"] = self.locale
        if self.timezone:
            options["tzone"] = self.timezone
        if self.proxy:
            options["proxy"] = self.proxy

        filter_first = bool(self.NETWORK_BLOCKED_EXTENSIONS)
        self._browser = sb_cdp.Chrome(None if filter_first else self.initial_url, **options)

        if self._download_directory:
            self._browser.set_download_path(self.download_directory)
        if filter_first:
            self._setup_network_extension_filter()
            self._browser.open(self.initial_url)
        self.statistics.add_request()

    def teardown_class(self) -> None:
        """Quit the browser. Safe to call before ``setup`` and more than once."""
        if self._browser is None:
            return
        try:
            self._browser.quit()
        finally:
            self._browser = None

    def _send(self, command: Any) -> Any:
        """Send a raw ``mycdp`` command (a generator such as ``cdp.network.enable()``)."""
        return self._browser.loop.run_until_complete(self._browser.page.send(command))

    @staticmethod
    def _js_element(selector: str) -> str:
        """Return a JavaScript expression resolving ``selector`` (CSS, or XPath when it starts with ``/`` or ``(``)."""
        if selector.startswith(("/", "(")):
            return (
                f"document.evaluate({json.dumps(selector)}, document, null, "
                "XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue"
            )
        return f"document.querySelector({json.dumps(selector)})"

    def evaluate(self, expression: str) -> Any:
        """Run a JavaScript expression in the page and return its value."""
        return self._browser.evaluate(expression)

    # --------------------------------------------------------------- Actions

    def go_to_url(self, url: str, delay_seconds_added: Optional[float] = None) -> None:
        """Navigate to ``url`` and record the request in the statistics tracker."""
        if delay_seconds_added:
            self.sleep(delay_seconds_added)
        self.statistics.add_request()
        self._browser.open(url)

    def send_keys(self, selector: str, value: str, use_script: bool = False, human: bool = False) -> None:  # type: ignore[override]
        """Append text to the element matching ``selector``.

        Args:
            selector: CSS selector of the target input.
            value: The text to enter.
            use_script: Set the value through JavaScript, dispatching ``input``
                and ``change`` events (no keyboard events).
            human: Type character by character with a variable rhythm; see
                :meth:`human_type`.

        Raises:
            ValueError: If both ``use_script`` and ``human`` are ``True``.
        """
        if use_script and human:
            raise ValueError("use_script and human are mutually exclusive")
        if human:
            self.human_type(selector, value)
        elif not use_script:
            self._browser.send_keys(selector, value, timeout=self.wait_seconds)
        else:
            self._browser.evaluate(
                f"""(() => {{
                    const element = {self._js_element(selector)};
                    const valueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    valueSetter.call(element, {json.dumps(value)});
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }})()"""
            )

    def human_type(self, selector: str, value: str, min_delay: float = 0.05, max_delay: float = 0.2) -> None:  # type: ignore[override]
        """Type text one character at a time with a variable rhythm.

        Args:
            selector: CSS selector of the target input.
            value: The text to type.
            min_delay: Minimum pause between characters, in seconds.
            max_delay: Maximum regular pause between characters, in seconds.
        """
        element = self._browser.find_element(selector, timeout=self.wait_seconds)
        loop = self._browser.loop
        for char, delay in zip(value, humanize.typing_delays(value, min_delay, max_delay)):
            loop.run_until_complete(element.send_keys_async(char))
            time.sleep(delay)

    def click_element(self, selector: str, use_script: bool = False, human: bool = False) -> None:  # type: ignore[override]
        """Click the element matching ``selector``.

        Args:
            selector: CSS selector of the element.
            use_script: Dispatch the click through JavaScript.
            human: Move the mouse along a curved path and click with real
                pointer events; see :meth:`move_mouse_to`.

        Raises:
            ValueError: If both ``use_script`` and ``human`` are ``True``.
        """
        if use_script and human:
            raise ValueError("use_script and human are mutually exclusive")
        if human:
            self.move_mouse_to(selector, click=True)
        elif not use_script:
            self._browser.click(selector, timeout=self.wait_seconds)
        else:
            self._browser.evaluate(f"{self._js_element(selector)}.click()")

    def move_mouse_to(self, selector: str, click: bool = False) -> None:  # type: ignore[override]
        """Move the mouse to a random point of an element along a curved path.

        The element is first scrolled into view gradually when it is outside the
        viewport. The pointer travels from its last known position (a random
        viewport point on first use) with eased speed, as CDP mouse events.

        Args:
            selector: CSS selector of the element.
            click: Press and release the left button on arrival, after a short
                human-like pause.
        """
        self._browser.find_element(selector, timeout=self.wait_seconds)
        rect = self._viewport_rect(selector)
        if rect["top"] < 0 or rect["bottom"] > rect["viewport_height"]:
            self.scroll_gradually(selector)
            rect = self._viewport_rect(selector)

        target = (
            round(rect["left"] + rect["width"] * random.uniform(0.3, 0.7)),
            round(rect["top"] + rect["height"] * random.uniform(0.3, 0.7)),
        )
        start = self._mouse_position or (
            round(random.uniform(0, rect["viewport_width"])),
            round(random.uniform(0, rect["viewport_height"])),
        )

        for x, y in humanize.mouse_path(start, target):
            self._send(cdp.input_.dispatch_mouse_event("mouseMoved", x, y, buttons=0))
            time.sleep(random.uniform(0.004, 0.018))
        self._mouse_position = target
        if click:
            x, y = target
            time.sleep(random.uniform(0.05, 0.15))
            self._send(
                cdp.input_.dispatch_mouse_event(
                    "mousePressed", x, y, button=cdp.input_.MouseButton.LEFT, buttons=1, click_count=1
                )
            )
            time.sleep(random.uniform(0.04, 0.12))
            self._send(
                cdp.input_.dispatch_mouse_event(
                    "mouseReleased", x, y, button=cdp.input_.MouseButton.LEFT, buttons=0, click_count=1
                )
            )

    def _viewport_rect(self, selector: str) -> dict[str, float]:  # type: ignore[override]
        """Return the element's viewport rectangle plus the viewport size."""
        left, top, width, height, viewport_width, viewport_height = self._browser.evaluate(
            f"""(() => {{
                const rect = {self._js_element(selector)}.getBoundingClientRect();
                return [rect.left, rect.top, rect.width, rect.height, window.innerWidth, window.innerHeight];
            }})()"""
        )
        return {
            "left": left,
            "top": top,
            "bottom": top + height,
            "width": width,
            "height": height,
            "viewport_width": viewport_width,
            "viewport_height": viewport_height,
        }

    def scroll_to_top(self) -> None:
        """Scroll the current page to the top."""
        self._browser.scroll_to_top()

    def scroll_to(self, target: str | int, y: Optional[int] = None) -> None:  # type: ignore[override]
        """Scroll to an element or to the given page coordinates.

        Args:
            target: CSS selector to bring into view, or the horizontal
                coordinate when scrolling to a position.
            y: Vertical coordinate. Required when ``target`` is an ``x`` value.

        Raises:
            ValueError: If a horizontal coordinate is supplied without ``y``.
        """
        if isinstance(target, str):
            self._browser.scroll_into_view(target, timeout=self.wait_seconds)
            return
        if y is None:
            raise ValueError("The y coordinate is required when scrolling to coordinates")
        self._browser.evaluate(f"window.scrollTo({int(target)}, {int(y)})")

    def scroll_to_bottom(self) -> None:
        """Scroll the current page to the bottom of its document."""
        self._browser.scroll_to_bottom()

    def scroll_gradually(self, target: str | int) -> None:  # type: ignore[override]
        """Scroll with real mouse wheel events in small, uneven steps.

        Args:
            target: CSS selector of an element to bring to the middle of the
                viewport, or a number of pixels to scroll (positive down).
        """
        if isinstance(target, str):
            rect = self._viewport_rect(target)
            distance = round(rect["top"] + rect["height"] / 2 - rect["viewport_height"] / 2)
        else:
            distance = int(target)
        if distance == 0:
            return

        viewport_width, viewport_height = self._browser.evaluate("[window.innerWidth, window.innerHeight]")
        x, y = self._mouse_position or (viewport_width // 2, viewport_height // 2)
        x, y = min(max(x, 0), viewport_width - 1), min(max(y, 0), viewport_height - 1)
        for step in humanize.scroll_steps(distance):
            self._send(cdp.input_.dispatch_mouse_event("mouseWheel", x, y, delta_x=0, delta_y=step))
            time.sleep(random.uniform(0.01, 0.06))
            if random.random() < 0.05:
                time.sleep(random.uniform(0.2, 0.5))

    # --------------------------------------------------------------- Network

    def _setup_network_extension_filter(self) -> None:
        """Block requests whose URL ends in :attr:`NETWORK_BLOCKED_EXTENSIONS` (CDP ``Network.setBlockedURLs``)."""
        if not self.NETWORK_BLOCKED_EXTENSIONS:
            return
        patterns = []
        for ext in self.NETWORK_BLOCKED_EXTENSIONS:
            ext = ext if ext.startswith(".") else f".{ext}"
            patterns.append(f"*{ext}")  # sin query string
            patterns.append(f"*{ext}?*")  # con query string / fragmento
        self._send(cdp.network.enable())
        self._send(cdp.network.set_blocked_urls(urls=patterns))
        self.logger.info(
            "[NetworkFilter] Blocked extensions: %s → %d URL patterns registered.",
            self.NETWORK_BLOCKED_EXTENSIONS,
            len(patterns),
        )

    def clear_blocked_extensions(self) -> None:
        """Remove all active extension-based network filters."""
        self.NETWORK_BLOCKED_EXTENSIONS = []
        if self._browser is not None:
            self._send(cdp.network.set_blocked_urls(urls=[]))
        self.logger.info("[NetworkFilter] Blocked extensions cleared.")

    def _apply_timezone(self) -> None:
        """Timezone is applied at launch through the ``tzone`` option."""
