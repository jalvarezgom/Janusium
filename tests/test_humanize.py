import random
from unittest.mock import MagicMock, patch

import pytest

from janusium import humanize
from janusium.drivers.selenium import SeleniumDriver


class DummyDriver(SeleniumDriver):
    _driver_type = "Dummy"


def test_mouse_path_ends_exactly_on_target():
    path = humanize.mouse_path((10, 10), (400, 300), rng=random.Random(1))

    assert path[-1] == (400, 300)
    assert len(path) >= 8


def test_mouse_path_is_curved_not_straight():
    path = humanize.mouse_path((0, 0), (500, 0), steps=30, rng=random.Random(3))

    assert any(y != 0 for _, y in path[:-1])


def test_mouse_path_rejects_invalid_steps():
    with pytest.raises(ValueError):
        humanize.mouse_path((0, 0), (10, 10), steps=0)


def test_typing_delays_one_per_character_within_bounds():
    delays = humanize.typing_delays("hello world", 0.05, 0.2, rng=random.Random(2))

    assert len(delays) == len("hello world")
    assert all(delay >= 0.05 for delay in delays)


def test_typing_delays_vary():
    delays = humanize.typing_delays("a" * 50, rng=random.Random(4))

    assert len(set(delays)) > 10


def test_typing_delays_rejects_invalid_range():
    with pytest.raises(ValueError):
        humanize.typing_delays("abc", 0.3, 0.1)


@pytest.mark.parametrize("distance", [500, -500, 37, 1])
def test_scroll_steps_sum_to_distance(distance):
    steps = humanize.scroll_steps(distance, rng=random.Random(5))

    assert sum(steps) == distance
    assert all((step > 0) == (distance > 0) for step in steps)


def test_scroll_steps_are_gradual():
    assert len(humanize.scroll_steps(1000, rng=random.Random(6))) > 5


def test_send_keys_human_types_each_character():
    driver = DummyDriver()
    element = MagicMock()

    with patch("janusium.drivers.selenium.time.sleep"):
        driver.send_keys(element, "abc", human=True)

    assert [call.args[0] for call in element.send_keys.call_args_list] == ["a", "b", "c"]


def test_send_keys_rejects_script_and_human_together():
    with pytest.raises(ValueError):
        DummyDriver().send_keys(MagicMock(), "abc", use_script=True, human=True)


def test_click_element_rejects_script_and_human_together():
    with pytest.raises(ValueError):
        DummyDriver().click_element(MagicMock(), use_script=True, human=True)


def test_scroll_gradually_zero_distance_does_nothing():
    driver = DummyDriver()
    driver._browser = MagicMock()

    driver.scroll_gradually(0)

    driver.browser.execute_script.assert_not_called()
