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


def test_validate_setup_passes_with_valid_configuration():
    driver = make_driver()
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


def test_download_directory_returns_none_when_not_configured():
    driver = make_driver()

    assert driver.download_directory is None


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


def test_get_random_sleep_time_within_bounds():
    driver = make_driver()

    for _ in range(50):
        delay = driver.get_random_sleep_time(1.0, 2.0)
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
