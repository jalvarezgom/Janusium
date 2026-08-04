# Janusium

[![PyPI](https://img.shields.io/pypi/v/janusium.svg)](https://pypi.org/project/janusium/)
[![Python](https://img.shields.io/pypi/pyversions/janusium.svg)](https://pypi.org/project/janusium/)
[![License](https://img.shields.io/pypi/l/janusium.svg)](LICENSE)

Selenium-based browser automation toolkit with anti-detection Chrome, Firefox,
and `undetected-chromedriver` drivers, request statistics, and network
filtering built in.

## Installation

```bash
pip install janusium[chrome]        # ChromeDriver (auto-managed via webdriver-manager)
pip install janusium[undetected]    # Anti-detection undetected-chromedriver
pip install janusium[all]           # Both, plus Firefox (no extra needed)
```

Firefox support only requires the base `selenium` dependency, so
`pip install janusium` is enough to use `FirefoxDriver`.

## Usage

Subclass `SeleniumDriver` (via `ChromeDriver`, `FirefoxDriver`, or
`UndetectedChromeDriver`), set `initial_url`, and implement `_run`:

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

## Development

```bash
pdm install -G test
pdm run pytest
```

## License

MIT — see [LICENSE](LICENSE).
