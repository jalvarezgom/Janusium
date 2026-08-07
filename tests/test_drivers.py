from janusium.drivers import ChromeDriver, FirefoxDriver, UndetectedChromeDriver
from janusium.drivers.selenium import SeleniumDriver
from janusium.statistics import StatisticsSelenium


def test_chrome_driver_is_a_selenium_driver_with_correct_type():
    assert issubclass(ChromeDriver, SeleniumDriver)
    assert ChromeDriver._driver_type == "Chrome"


def test_firefox_driver_is_a_selenium_driver_with_correct_type():
    assert issubclass(FirefoxDriver, SeleniumDriver)
    assert FirefoxDriver._driver_type == "Firefox"


def test_undetected_chrome_driver_is_a_selenium_driver_with_correct_type():
    assert issubclass(UndetectedChromeDriver, SeleniumDriver)
    assert UndetectedChromeDriver._driver_type == "UndetectedChrome"


def test_firefox_driver_stores_optional_service_options():
    driver = FirefoxDriver(
        executable_path="C:/geckodriver.exe",
        log_path="C:/geckodriver.log",
        service_args=["--marionette-port", "2828"],
    )

    assert driver.executable_path == "C:/geckodriver.exe"
    assert driver.log_path == "C:/geckodriver.log"
    assert driver.service_args == ["--marionette-port", "2828"]


def test_firefox_driver_defaults_service_options_to_none():
    driver = FirefoxDriver()

    assert driver.executable_path is None
    assert driver.log_path is None
    assert driver.service_args is None


def test_firefox_driver_initializes_base_selenium_driver_state():
    driver = FirefoxDriver(headless_browser=False, wait_seconds=7)

    assert isinstance(driver.statistics, StatisticsSelenium)
    assert driver.headless_browser is False
    assert driver.wait_seconds == 7
