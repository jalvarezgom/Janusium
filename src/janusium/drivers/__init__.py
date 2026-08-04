from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from janusium.drivers.chrome import ChromeDriver
    from janusium.drivers.firefox import FirefoxDriver
    from janusium.drivers.undetected_chrome import UndetectedChromeDriver

__all__ = ["ChromeDriver", "FirefoxDriver", "UndetectedChromeDriver"]


def __getattr__(name):
    # Imports deferred so that installing e.g. `janusium[undetected]` isn't
    # required just to use FirefoxDriver, which only needs base `selenium`.
    if name == "ChromeDriver":
        from janusium.drivers.chrome import ChromeDriver

        return ChromeDriver
    if name == "FirefoxDriver":
        from janusium.drivers.firefox import FirefoxDriver

        return FirefoxDriver
    if name == "UndetectedChromeDriver":
        from janusium.drivers.undetected_chrome import UndetectedChromeDriver

        return UndetectedChromeDriver
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
