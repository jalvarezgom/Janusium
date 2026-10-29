import importlib
import sys
import os
from unittest.mock import MagicMock

import pytest

from janusium.drivers import ChromeDriver, FirefoxDriver, SeleniumBaseUCDriver, UndetectedChromeDriver
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


def test_firefox_driver_rejects_unknown_options():
    with pytest.raises(TypeError):
        FirefoxDriver(headles_browser=False)


def test_firefox_driver_stores_custom_preferences_and_forwards_base_options():
    driver = FirefoxDriver(custom_preferences=[("a.b", 1)], headless_browser=False, wait_seconds=7)

    assert ("a.b", 1) in list(driver._iter_preferences())
    assert driver.headless_browser is False
    assert driver.wait_seconds == 7


def _download_dir_variants(tmp_path):
    posix_style = str(tmp_path).replace("\\", "/")
    return posix_style, os.path.normpath(posix_style)


def test_chrome_driver_normalizes_download_directory(tmp_path, monkeypatch):
    from janusium.drivers import chrome

    captured = {}
    monkeypatch.setattr(chrome, "ChromeDriverManager", lambda: MagicMock(install=lambda: "chromedriver"))
    monkeypatch.setattr(chrome.webdriver, "Chrome", lambda service, options: captured.setdefault("options", options) and MagicMock())
    given, expected = _download_dir_variants(tmp_path)

    ChromeDriver(download_directory=given)._launch_browser()

    prefs = captured["options"].experimental_options["prefs"]
    assert prefs["download.default_directory"] == expected


def test_undetected_chrome_driver_normalizes_download_directory(tmp_path, monkeypatch):
    from janusium.drivers import undetected_chrome

    captured = {}
    monkeypatch.setattr(
        undetected_chrome.uc, "Chrome", lambda options, **kw: captured.setdefault("options", options) and MagicMock()
    )
    given, expected = _download_dir_variants(tmp_path)
    driver = UndetectedChromeDriver(download_directory=given)

    driver._launch_browser()

    prefs = captured["options"].experimental_options["prefs"]
    assert prefs["download.default_directory"] == expected
    driver._owns_browser = False


def test_firefox_driver_normalizes_download_directory(tmp_path, monkeypatch):
    from janusium.drivers import firefox

    captured = {}
    monkeypatch.setattr(firefox.webdriver, "Firefox", lambda options: captured.setdefault("options", options) and MagicMock())
    given, expected = _download_dir_variants(tmp_path)

    FirefoxDriver(download_directory=given)._launch_browser()

    assert captured["options"].preferences["browser.download.dir"] == expected


def test_chrome_driver_does_not_patch_navigator_or_force_user_agent(tmp_path, monkeypatch):
    from janusium.drivers import chrome

    captured = {}
    browser = MagicMock()
    monkeypatch.setattr(chrome, "ChromeDriverManager", lambda: MagicMock(install=lambda: "chromedriver"))
    monkeypatch.setattr(chrome.webdriver, "Chrome", lambda service, options: captured.setdefault("options", options) and browser)

    ChromeDriver(download_directory=str(tmp_path))._launch_browser()

    assert not any(a.startswith("--user-agent") for a in captured["options"].arguments)
    commands = [call.args[0] for call in browser.execute_cdp_cmd.call_args_list]
    assert "Page.addScriptToEvaluateOnNewDocument" not in commands


def test_chrome_driver_applies_locale_user_agent_and_timezone(tmp_path, monkeypatch):
    from janusium.drivers import chrome

    captured = {}
    browser = MagicMock()
    monkeypatch.setattr(chrome, "ChromeDriverManager", lambda: MagicMock(install=lambda: "chromedriver"))
    monkeypatch.setattr(chrome.webdriver, "Chrome", lambda service, options: captured.setdefault("options", options) and browser)

    ChromeDriver(
        download_directory=str(tmp_path), user_agent="Custom/1.0", locale="es-ES", timezone="Europe/Madrid"
    )._launch_browser()

    arguments = captured["options"].arguments
    assert "--user-agent=Custom/1.0" in arguments
    assert "--lang=es-ES" in arguments
    assert "--accept-lang=es-ES,es" in arguments
    browser.execute_cdp_cmd.assert_called_with("Emulation.setTimezoneOverride", {"timezoneId": "Europe/Madrid"})


def test_firefox_driver_applies_user_agent_and_languages_as_preferences():
    driver = FirefoxDriver(user_agent="Custom/1.0", locale="es-ES")

    preferences = dict(driver._iter_preferences())
    assert preferences["general.useragent.override"] == "Custom/1.0"
    assert preferences["intl.accept_languages"] == "es-ES,es"


@pytest.mark.parametrize(
    "module, blocked, extra",
    [
        ("janusium.drivers.chrome", "webdriver_manager", "chrome"),
        ("janusium.drivers.undetected_chrome", "undetected_chromedriver", "undetected"),
        ("janusium.drivers.seleniumbase_uc", "seleniumbase", "seleniumbase"),
        ("janusium.drivers.seleniumbase_cdp", "seleniumbase", "seleniumbase"),
    ],
)
def test_missing_optional_dependency_explains_how_to_install_it(module, blocked, extra, monkeypatch):
    monkeypatch.setitem(sys.modules, blocked, None)
    monkeypatch.setitem(sys.modules, f"{blocked}.chrome", None)
    monkeypatch.delitem(sys.modules, module, raising=False)

    with pytest.raises(ImportError, match=rf"pip install janusium\[{extra}\]"):
        importlib.import_module(module)


def test_seleniumbase_uc_driver_passes_arguments_with_commas_as_a_list(monkeypatch):
    pytest.importorskip("seleniumbase")
    from janusium.drivers import seleniumbase_uc

    captured = {}
    monkeypatch.setattr(seleniumbase_uc, "Driver", lambda **options: captured.update(options) or MagicMock())

    driver = SeleniumBaseUCDriver(custom_arguments=["--window-size=1920,1080", "--accept-lang=es-ES,es"])
    driver._launch_browser()
    driver._owns_browser = False

    assert isinstance(captured["chromium_arg"], list)
    assert "--window-size=1920,1080" in captured["chromium_arg"]
    assert "--accept-lang=es-ES,es" in captured["chromium_arg"]
