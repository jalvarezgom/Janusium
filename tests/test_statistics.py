from datetime import datetime, timedelta

from janusium.statistics import StatisticsSelenium


def test_starts_with_no_requests_and_no_timers():
    stats = StatisticsSelenium()

    assert stats.TOTAL_REQUESTS == 0
    assert stats.START_TIME is None
    assert stats.END_TIME is None


def test_add_request_increments_counter():
    stats = StatisticsSelenium()

    stats.add_request()
    stats.add_request()

    assert stats.TOTAL_REQUESTS == 2


def test_add_request_does_not_leak_between_instances():
    first = StatisticsSelenium()
    second = StatisticsSelenium()

    first.add_request()

    assert first.TOTAL_REQUESTS == 1
    assert second.TOTAL_REQUESTS == 0


def test_start_and_end_timer_set_datetimes():
    stats = StatisticsSelenium()

    stats.start_timer()
    stats.end_timer()

    assert isinstance(stats.START_TIME, datetime)
    assert isinstance(stats.END_TIME, datetime)


def test_get_seconds_timer_returns_none_when_timers_not_set():
    stats = StatisticsSelenium()

    assert stats.get_seconds_timer() is None

    stats.start_timer()
    assert stats.get_seconds_timer() is None


def test_get_seconds_timer_returns_elapsed_duration():
    stats = StatisticsSelenium()
    stats.START_TIME = datetime(2024, 1, 1, 12, 0, 0)
    stats.END_TIME = stats.START_TIME + timedelta(seconds=5)

    assert stats.get_seconds_timer() == 5.0


def test_repr_contains_class_name_and_values():
    stats = StatisticsSelenium()
    stats.add_request()

    representation = repr(stats)

    assert "StatisticsSelenium" in representation
    assert "TOTAL_REQUESTS=1" in representation
