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
`UndetectedChromeDriver`, or `SeleniumBaseUCDriver`), set `initial_url`, and implement `_run`:

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

### Helpers

- `go_to_url()`: navigate and count the request in `statistics`.
- `click_element()`, `send_keys()`: interact with elements; pass `use_script=True`
  to go through JavaScript.
- `scroll_to()`, `scroll_to_top()`, `scroll_to_bottom()`: page scrolling.
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
