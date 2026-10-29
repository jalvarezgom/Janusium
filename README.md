# Janusium

[![PyPI](https://img.shields.io/pypi/v/janusium.svg)](https://pypi.org/project/janusium/)
[![Python](https://img.shields.io/pypi/pyversions/janusium.svg)](https://pypi.org/project/janusium/)
[![License](https://img.shields.io/pypi/l/janusium.svg)](LICENSE)

Selenium-based browser automation toolkit with anti-detection Chrome, Firefox,
`undetected-chromedriver` and SeleniumBase UC drivers, request statistics, and
network filtering built in.

## Installation

```bash
pip install janusium[chrome]        # ChromeDriver (auto-managed via webdriver-manager)
pip install janusium[undetected]    # Anti-detection undetected-chromedriver
pip install janusium[seleniumbase]  # SeleniumBase UC mode
pip install janusium[all]           # All of the above (Firefox needs no extra)
```

Firefox support only requires the base `selenium` dependency, so
`pip install janusium` is enough to use `FirefoxDriver`.

## Usage

Subclass `SeleniumDriver` (via `ChromeDriver`, `FirefoxDriver`,
`UndetectedChromeDriver`, `SeleniumBaseUCDriver`, or `SeleniumBaseCDPDriver`), set `initial_url`, and implement `_run`:

```python
from janusium.drivers import ChromeDriver


class ExampleScraper(ChromeDriver):
    initial_url = "https://example.com"

    def _run(self, **params):
        return self.browser.title


scraper = ExampleScraper(headless_browser=True)
scraper.setup()
title, error = scraper.run()
print(title)
```

### Anti-detection & network filtering

```python
class ExampleScraper(ChromeDriver):
    initial_url = "https://example.com"
    NETWORK_BLOCKED_EXTENSIONS = [".jpg", ".png", ".css"]
    NETWORK_DOMAIN_WHITELIST = ["example.com"]

    def _run(self, **params):
        self.random_sleep()
        return self.browser.title
```

### Configuration

All drivers accept these keyword arguments:

| Argument | Default | Description |
| --- | --- | --- |
| `headless_browser` | `True` | Run without a visible window. |
| `wait_seconds` | `3` | Implicit and explicit wait timeout, in seconds. |
| `download_directory` | `None` | Existing directory for downloads. Required unless an existing `browser` is passed (optional for `SeleniumBaseUCDriver`). |
| `browser` | `None` | Existing WebDriver to reuse instead of launching a new one. |
| `logger` | `logging.getLogger("janusium")` | Logger used for driver messages. |
| `custom_arguments` | `None` | Extra browser command-line arguments. |
| `user_agent` | `None` | User-Agent to send. By default the browser keeps its own, which stays consistent with its real version. |
| `locale` | `None` | Browser locale, e.g. `"es-ES"`. Also derives `languages` when those are not given. |
| `languages` | `None` | Ordered `Accept-Language` / `navigator.languages` values, e.g. `["es-ES", "en-US"]`. |
| `timezone` | `None` | IANA timezone id, e.g. `"Europe/Madrid"`. Chromium drivers only (applied through CDP). |

Driver-specific arguments:

| Driver | Argument | Description |
| --- | --- | --- |
| `FirefoxDriver` | `executable_path`, `log_path`, `service_args` | GeckoDriver service settings. |
| `FirefoxDriver` | `custom_preferences` | Extra Firefox `(name, value)` preferences. |
| `UndetectedChromeDriver` | `chrome_version` | Chrome major version to pin the driver to. |
| `SeleniumBaseUCDriver` | `chrome_version` | Chrome major version to pin the driver to. |
| `SeleniumBaseUCDriver` | `proxy` | `HOST:PORT` or `USER:PASSWORD@HOST:PORT`. |
| `SeleniumBaseCDPDriver` | `proxy` | `HOST:PORT` or `USER:PASSWORD@HOST:PORT`. |

Unknown arguments raise `TypeError`. Browser arguments can also be added before
`setup()` with `add_argument()` / `add_arguments()`.

```python
scraper = ExampleScraper(
    headless_browser=True,
    download_directory="C:/downloads",
    locale="es-ES",
    timezone="Europe/Madrid",
)
```

`locale`, `languages` and `timezone` are applied through native browser
switches and CDP rather than by patching `navigator` from JavaScript, and
`user_agent` is left to the browser by default so every signal stays coherent.
Firefox applies `user_agent` and `languages` as preferences and ignores
`timezone` (it has no CDP).

### SeleniumBase UC vs CDP

Both drivers are configured with the same keyword arguments (`headless_browser`,
`proxy`, `locale`, `timezone`, `user_agent`, ...). The difference is how you find
and click elements: UC exposes a Selenium `browser` and works with `WebElement`s,
while CDP works with selector strings (CSS or XPath).

**UC mode** (`SeleniumBaseUCDriver`): configure, find an element and click it.

```python
from selenium.webdriver.common.by import By

from janusium.drivers import SeleniumBaseUCDriver


class UCScraper(SeleniumBaseUCDriver):
    initial_url = "https://example.com"

    def _run(self, **params):
        link = self.browser.find_element(By.CSS_SELECTOR, "a")  # Selenium WebElement
        self.click_element(link, human=True)  # curved mouse path + real click
        return self.browser.current_url


scraper = UCScraper(
    headless_browser=False,
    proxy="user:password@proxy.example.com:8080",  # optional
    locale="es-ES",
    timezone="Europe/Madrid",
    chrome_version=126,  # optional: pin the Chrome major version
).setup()
try:
    url, error = scraper.run()
finally:
    scraper.teardown_class()
```

**CDP mode** (`SeleniumBaseCDPDriver`): same configuration, but elements are CSS
selector strings and there is no Selenium `WebDriver`; `self.browser` and
`self.cdp` both point to the SeleniumBase CDP object.

```python
from janusium.drivers import SeleniumBaseCDPDriver


class CDPScraper(SeleniumBaseCDPDriver):
    initial_url = "https://example.com"

    def _run(self, **params):
        self.cdp.assert_element("a")  # find the element (waits until it exists)
        self.click_element("a", human=True)  # curved mouse path + real click via CDP
        return self.cdp.get_current_url()


scraper = CDPScraper(
    headless_browser=False,  # a visible window is harder to detect
    proxy="user:password@proxy.example.com:8080",  # optional
    locale="es-ES",
    timezone="Europe/Madrid",
).setup()
try:
    url, error = scraper.run()
finally:
    scraper.teardown_class()
```

#### Same operation, two ways

`SeleniumBaseCDPDriver` starts Chrome through SeleniumBase's CDP Mode
(`sb_cdp.Chrome`): no chromedriver and no WebDriver session, so there are fewer
automation traces. `human=True` is replayed as CDP `Input` events, so it works
headless and does not move the OS cursor. The examples above use these
equivalents:

| Operation | UC (`SeleniumBaseUCDriver`) | CDP (`SeleniumBaseCDPDriver`) |
| --- | --- | --- |
| Open a URL | `self.go_to_url(url)` | `self.go_to_url(url)` |
| Find an element | `self.browser.find_element(By.CSS_SELECTOR, "a")` | `self.cdp.find_element("a")` / `self.cdp.assert_element("a")` |
| Click | `self.click_element(link)` | `self.click_element("a")` |
| Human click | `self.click_element(link, human=True)` | `self.click_element("a", human=True)` |
| Type | `self.send_keys(field, "text")` | `self.send_keys("#q", "text")` |
| Read text | `link.text` | `self.cdp.get_text("a")` |
| Wait for an element | `self.wait_driver.until(EC.presence_of_element_located(...))` | `self.cdp.wait_for_element("a")` |
| Run JavaScript | `self.browser.execute_script("return 1", link)` | `self.evaluate("1")` |
| Scroll to an element | `self.scroll_to(link)` | `self.scroll_to("a")` |
| Current URL | `self.browser.current_url` | `self.cdp.get_current_url()` |
| Block extensions, statistics, `teardown_class()` | same | same |

#### CDP limitations compared to UC

- **No Selenium objects.** There is no `WebDriver`, `WebElement`, `By`,
  `ActionChains`, `WebDriverWait` or `execute_cdp_cmd`, and `wait_driver` is
  `None`. Code or libraries written against Selenium (page objects, expected
  conditions) do not work; use the SeleniumBase waits on `self.cdp`.
- **Selectors, not elements.** Actions take selector strings: CSS, or XPath
  when it starts with `/` or `(` (e.g. `"//a"`). You cannot pass an element
  object around as with Selenium's `WebElement`.
- **No `browser=` and no `chrome_version`.** UC can reuse an existing browser and
  pin the Chrome major version; CDP raises `TypeError` for both.
- **Identity is fixed at launch.** `user_agent`, `timezone`, `locale`, `proxy`
  and `languages` are applied when Chrome starts; SeleniumBase CDP has no
  runtime setter for the user-agent or the timezone (`set_locale` only takes
  effect on the next page load).
- **Smaller, different API.** Anything not wrapped by Janusium goes through
  `self.cdp` (SeleniumBase) or raw `mycdp` commands with `self._send(...)`, for
  example `self._send(cdp.emulation.set_timezone_override("Europe/Madrid"))`.
- **JavaScript is expression-based.** `self.evaluate()` takes one expression (a
  trailing `return` is stripped); wrap multi-statement code in an IIFE:
  `self.evaluate("(() => { const a = 1; return a + 1; })()")`.
- **Headless is easier to detect.** CDP Mode works best with a visible window,
  and SeleniumBase's `gui_*` helpers drive the OS cursor, so they need one.
- **No hybrid mode.** The driver does not switch between WebDriver and CDP in
  one session; pick UC or CDP per scraper.

### Helpers

- `go_to_url()`: navigate and count the request in `statistics`.
- `click_element()`, `send_keys()`: interact with elements; pass `use_script=True`
  to go through JavaScript (no real keyboard events), or `human=True` for
  human-like input (mutually exclusive with `use_script`).
- `human_type()`: types character by character with real key events and a
  variable rhythm (longer after spaces and punctuation, occasional hesitations).
  `send_keys(..., human=True)` calls it.
- `move_mouse_to()`: moves the mouse along a curved, eased path with real pointer
  events; `click=True` (or `click_element(..., human=True)`) also clicks.
- `scroll_gradually()`: scrolls with real wheel events in small uneven steps, to
  an element or by a number of pixels.
- `scroll_to()`, `scroll_to_top()`, `scroll_to_bottom()`: instant page scrolling.
- `random_sleep()`, `sleep()`: pauses to simulate human pacing.
- `clean_download_directory()`: removes files (not subdirectories) from the
  download directory.
- `set_blocked_extensions()` / `clear_blocked_extensions()`: change network
  filtering at runtime (Chromium only).
- `statistics`: request count and run duration (`StatisticsSelenium`).
- `teardown_class()`: quits the browser; safe to call more than once.

## Development

```bash
pdm install -G test
pdm run pytest
```

## License

MIT — see [LICENSE](LICENSE).
