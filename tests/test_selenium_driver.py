from unittest.mock import MagicMock

import pytest

from janusium.drivers.selenium import SeleniumDriver, _SELENIUM_USER_AGENTS


class DummyDriver(SeleniumDriver):
    _driver_type = "Dummy"


def make_driver(**kwargs):
    return DummyDriver(**kwargs)


def test_validate_setup_raises_without_driver_type():
    driver = SeleniumDriver()
    driver.initial_url = "https://example.com"

    with pytest.raises(Exception, match="isn't a valid driver class"):
        driver._validate_setup()


@pytest.mark.parametrize("wait_seconds", [0, None, "3"])
def test_validate_setup_raises_with_invalid_wait_seconds(wait_seconds):
    driver = make_driver(wait_seconds=wait_seconds)
    driver.initial_url = "https://example.com"

    with pytest.raises(Exception, match="wait_seconds"):
        driver._validate_setup()


def test_validate_setup_raises_without_initial_url():
    driver = make_driver()

    with pytest.raises(Exception, match="initial_url"):
        driver._validate_setup()


def test_validate_setup_raises_without_download_directory():
    driver = make_driver()
    driver.initial_url = "https://example.com"

    with pytest.raises(Exception, match="download_directory"):
        driver._validate_setup()


def test_validate_setup_passes_with_valid_configuration(tmp_path):
    driver = make_driver(download_directory=str(tmp_path))
    driver.initial_url = "https://example.com"

    driver._validate_setup()


def test_validate_fields_raises_when_required_field_missing():
    driver = make_driver()
    driver.required_fields = ["username", "password"]

    with pytest.raises(Exception, match="username"):
        driver._validate_fields({"password": "secret"})


def test_validate_fields_passes_when_all_present():
    driver = make_driver()
    driver.required_fields = ["username"]

    driver._validate_fields({"username": "john"})


def test_download_directory_raises_when_not_configured():
    driver = make_driver()

    with pytest.raises(Exception, match="download_directory"):
        driver.download_directory


def test_download_directory_raises_when_path_missing():
    driver = make_driver(download_directory="Z:/definitely/not/a/real/path")

    with pytest.raises(Exception, match="doesn't exist"):
        driver.download_directory


def test_download_directory_returns_path_when_it_exists(tmp_path):
    driver = make_driver(download_directory=str(tmp_path))

    assert driver.download_directory == str(tmp_path)


def test_get_random_user_agent_returns_known_agent():
    driver = make_driver()

    assert driver.get_random_user_agent() in _SELENIUM_USER_AGENTS


def test_get_random_time_within_bounds():
    driver = make_driver()

    for _ in range(50):
        delay = driver.get_random_time(1.0, 2.0)
        assert 1.0 <= delay <= 2.0


def test_build_host_rules_argument_returns_none_when_whitelist_empty():
    driver = make_driver()
    driver.NETWORK_DOMAIN_WHITELIST = []

    assert driver._build_host_rules_argument() is None


def test_build_host_rules_argument_builds_expected_rule():
    driver = make_driver()
    driver.NETWORK_DOMAIN_WHITELIST = ["example.com", "example.org"]

    host_rules = driver._build_host_rules_argument()

    assert host_rules == "MAP * ~NOTFOUND, EXCLUDE example.com, EXCLUDE example.org"


def test_run_raises_not_implemented_by_default():
    driver = make_driver()

    with pytest.raises(NotImplementedError):
        driver.run()


def test_run_returns_exception_instead_of_raising_when_disabled():
    driver = make_driver()

    data, exception = driver.run(raise_exceptions=False)

    assert data is None
    assert isinstance(exception, NotImplementedError)


def test_run_validates_required_fields_before_running():
    driver = make_driver()
    driver.required_fields = ["username"]

    with pytest.raises(Exception, match="username"):
        driver.run()


def test_teardown_class_quits_browser_and_clears_state():
    browser = MagicMock()
    driver = make_driver(browser=browser)

    driver.teardown_class()

    browser.quit.assert_called_once()
    assert driver.browser is None
    assert driver.wait_driver is None


def test_teardown_class_without_browser_does_not_raise():
    driver = make_driver()

    driver.teardown_class()


def test_teardown_class_is_idempotent():
    browser = MagicMock()
    driver = make_driver(browser=browser)

    driver.teardown_class()
    driver.teardown_class()

    browser.quit.assert_called_once()


def test_teardown_class_clears_state_even_if_quit_fails():
    browser = MagicMock()
    browser.quit.side_effect = RuntimeError("boom")
    driver = make_driver(browser=browser)

    with pytest.raises(RuntimeError):
        driver.teardown_class()

    assert driver.browser is None


def test_clean_download_directory_removes_files_and_keeps_subdirectories(tmp_path):
    (tmp_path / "a.csv").write_text("a")
    (tmp_path / "b.xlsx").write_text("b")
    subdir = tmp_path / "partial"
    subdir.mkdir()
    (subdir / "c.crdownload").write_text("c")
    driver = make_driver(download_directory=str(tmp_path))

    driver.clean_download_directory()

    assert not (tmp_path / "a.csv").exists()
    assert not (tmp_path / "b.xlsx").exists()
    assert (subdir / "c.crdownload").exists()


def test_clean_download_directory_with_empty_directory_does_not_raise(tmp_path):
    make_driver(download_directory=str(tmp_path)).clean_download_directory()


def test_identity_arguments_are_empty_by_default():
    assert list(make_driver()._iter_identity_arguments()) == []


def test_identity_arguments_include_user_agent_only_when_given():
    driver = make_driver(user_agent="Custom/1.0")

    assert list(driver._iter_identity_arguments()) == ["--user-agent=Custom/1.0"]


def test_locale_derives_lang_and_accept_languages():
    driver = make_driver(locale="es-ES")

    assert list(driver._iter_identity_arguments()) == ["--lang=es-ES", "--accept-lang=es-ES,es"]


def test_explicit_languages_override_the_locale_derived_ones():
    driver = make_driver(locale="es-ES", languages=["es-ES", "en-US"])

    assert "--accept-lang=es-ES,en-US" in driver._iter_identity_arguments()


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"user_agent": ""}, ValueError),
        ({"locale": 5}, ValueError),
        ({"timezone": ""}, ValueError),
        ({"languages": "es-ES"}, TypeError),
        ({"languages": ["es", ""]}, ValueError),
    ],
)
def test_invalid_identity_options_are_rejected(kwargs, error):
    with pytest.raises(error):
        make_driver(**kwargs)


def test_apply_timezone_uses_cdp_override():
    browser = MagicMock()
    driver = make_driver(browser=browser, timezone="Europe/Madrid")

    driver._apply_timezone()

    browser.execute_cdp_cmd.assert_called_once_with("Emulation.setTimezoneOverride", {"timezoneId": "Europe/Madrid"})


def test_apply_timezone_is_noop_without_timezone():
    browser = MagicMock()

    make_driver(browser=browser)._apply_timezone()

    browser.execute_cdp_cmd.assert_not_called()
