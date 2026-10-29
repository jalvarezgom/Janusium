from importlib import import_module

_LAZY_IMPORTS = {
    "ChromeDriver": "janusium.drivers.chrome",
    "FirefoxDriver": "janusium.drivers.firefox",
    "UndetectedChromeDriver": "janusium.drivers.undetected_chrome",
    "SeleniumBaseUCDriver": "janusium.drivers.seleniumbase_uc",
    "SeleniumBaseCDPDriver": "janusium.drivers.seleniumbase_cdp",
}

__all__ = list(_LAZY_IMPORTS)


def __getattr__(name):
    # Drivers are imported on demand so optional dependencies (webdriver-manager,
    # undetected-chromedriver, seleniumbase) are only required for the driver used.
    if name in _LAZY_IMPORTS:
        return getattr(import_module(_LAZY_IMPORTS[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
