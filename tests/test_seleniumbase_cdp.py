from unittest.mock import MagicMock

import pytest

from janusium.drivers import SeleniumBaseCDPDriver
from janusium.drivers import seleniumbase_cdp
from janusium.drivers.selenium import SeleniumDriver


class _Driver(SeleniumBaseCDPDriver):
    initial_url = "https://example.com"


@pytest.fixture
def chrome(monkeypatch):
    """Replace ``sb_cdp.Chrome`` and record the options it was launched with."""
    instance = MagicMock()
    factory = MagicMock(return_value=instance)
    monkeypatch.setattr(seleniumbase_cdp.sb_cdp, "Chrome", factory)
    instance.factory = factory
    return instance


def test_is_a_selenium_driver_with_correct_type():
    assert issubclass(SeleniumBaseCDPDriver, SeleniumDriver)
    assert SeleniumBaseCDPDriver._driver_type == "SeleniumBaseCDP"


def test_rejects_unknown_options():
    with pytest.raises(TypeError):
        SeleniumBaseCDPDriver(browser=MagicMock())


def test_setup_launches_on_initial_url_and_exposes_cdp(chrome):
    driver = _Driver().setup()

    url = chrome.factory.call_args.args[0]
    assert url == "https://example.com"
    assert driver.cdp is chrome
    driver.teardown_class()


def test_setup_requires_initial_url():
    with pytest.raises(Exception, match="initial_url"):
        SeleniumBaseCDPDriver().setup()


def test_launch_maps_identity_proxy_and_headless_options(chrome):
    _Driver(
        headless_browser=False,
        proxy="user:pw@host:80",
        user_agent="Custom/1.0",
        locale="es-ES",
        timezone="Europe/Madrid",
        custom_arguments=["--mute-audio"],
    ).setup()

    options = chrome.factory.call_args.kwargs
    assert options["headless"] is False
    assert options["proxy"] == "user:pw@host:80"
    assert options["agent"] == "Custom/1.0"
    assert options["lang"] == "es-ES"
    assert options["tzone"] == "Europe/Madrid"
    assert "--mute-audio" in options["browser_args"]
    assert "--accept-lang=es-ES,es" in options["browser_args"]


def test_launch_applies_domain_whitelist_as_host_rules(chrome):
    class Whitelisted(_Driver):
        NETWORK_DOMAIN_WHITELIST = ["example.com"]

    Whitelisted().setup()

    arguments = chrome.factory.call_args.kwargs["browser_args"]
    assert any(a.startswith("--host-rules=MAP * ~NOTFOUND") for a in arguments)


def test_launch_sets_download_path(chrome, tmp_path):
    _Driver(download_directory=str(tmp_path)).setup()

    chrome.set_download_path.assert_called_once_with(str(tmp_path))


def test_setup_does_not_require_download_directory(chrome):
    _Driver().setup()


def test_blocked_extensions_register_url_patterns(chrome):
    class Blocking(_Driver):
        NETWORK_BLOCKED_EXTENSIONS = ["png", ".css"]

    Blocking().setup()

    assert chrome.page.send.call_count == 2  # Network.enable + Network.setBlockedURLs


def test_blocked_extensions_are_registered_before_the_first_navigation(chrome):
    class Blocking(_Driver):
        NETWORK_BLOCKED_EXTENSIONS = [".png"]

    calls = []
    chrome.factory.side_effect = lambda *a, **k: calls.append(("launch", a[0])) or chrome
    chrome.page.send.side_effect = lambda *a, **k: calls.append(("filter",))
    chrome.open.side_effect = lambda url: calls.append(("open", url))

    driver = Blocking().setup()

    assert calls[0] == ("launch", None)
    assert calls[-1] == ("open", "https://example.com")
    assert ("filter",) in calls[1:-1]
    assert str(driver.statistics).count("TOTAL_REQUESTS=1") == 1


def test_without_filter_the_browser_launches_directly_on_initial_url(chrome):
    _Driver().setup()

    assert chrome.factory.call_args.args[0] == "https://example.com"
    chrome.open.assert_not_called()


def test_go_to_url_opens_and_counts_the_request(chrome):
    driver = _Driver().setup()
    before = str(driver.statistics)

    driver.go_to_url("https://example.org")

    chrome.open.assert_called_with("https://example.org")
    assert str(driver.statistics) != before


def test_click_element_modes(chrome):
    driver = _Driver(wait_seconds=5).setup()

    driver.click_element("#a")
    chrome.click.assert_called_once_with("#a", timeout=5)

    driver.click_element("#a", use_script=True)
    assert "querySelector(\"#a\").click()" in chrome.evaluate.call_args.args[0]

    with pytest.raises(ValueError):
        driver.click_element("#a", use_script=True, human=True)


def test_send_keys_modes(chrome):
    driver = _Driver(wait_seconds=5).setup()

    driver.send_keys("#q", "hola")
    chrome.send_keys.assert_called_once_with("#q", "hola", timeout=5)

    driver.send_keys("#q", "hola", use_script=True)
    assert '"hola"' in chrome.evaluate.call_args.args[0]

    with pytest.raises(ValueError):
        driver.send_keys("#q", "hola", use_script=True, human=True)


def test_human_click_dispatches_moves_then_press_and_release(chrome, monkeypatch):
    monkeypatch.setattr(seleniumbase_cdp.time, "sleep", lambda _: None)
    seen = []
    monkeypatch.setattr(
        seleniumbase_cdp.cdp.input_, "dispatch_mouse_event", lambda type_, *a, **k: seen.append(type_) or type_
    )
    chrome.evaluate.return_value = [100, 100, 50, 20, 1000, 800]
    driver = _Driver().setup()

    driver.click_element("#a", human=True)

    assert seen[-2:] == ["mousePressed", "mouseReleased"]
    assert set(seen[:-2]) == {"mouseMoved"}
    assert driver._mouse_position is not None


@pytest.mark.parametrize("selector", ["//a", "(//a)[2]"])
def test_xpath_selectors_are_resolved_with_document_evaluate(chrome, selector):
    chrome.evaluate.return_value = [0, 0, 10, 10, 100, 100]
    driver = _Driver().setup()

    driver.click_element(selector, use_script=True)
    driver._viewport_rect(selector)

    scripts = [call.args[0] for call in chrome.evaluate.call_args_list]
    assert all("document.evaluate" in script and "querySelector" not in script for script in scripts)


def test_css_selectors_are_resolved_with_query_selector(chrome):
    driver = _Driver().setup()

    driver.click_element("a.btn", use_script=True)

    assert 'document.querySelector("a.btn")' in chrome.evaluate.call_args.args[0]


def test_scroll_to_coordinates_requires_y(chrome):
    driver = _Driver().setup()

    with pytest.raises(ValueError):
        driver.scroll_to(10)


def test_teardown_is_idempotent_and_safe_without_setup(chrome):
    _Driver().teardown_class()
    driver = _Driver().setup()

    driver.teardown_class()
    driver.teardown_class()

    chrome.quit.assert_called_once()
    assert driver.cdp is None
