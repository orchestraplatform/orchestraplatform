"""Tests for time and duration utilities."""

from datetime import datetime, timedelta, timezone

import pytest

from utils.time_utils import get_expiration_time, is_expired, parse_duration, time_until_expiration


class TestParseDuration:
    def test_hours_only(self):
        assert parse_duration("4h") == timedelta(hours=4)

    def test_minutes_only(self):
        assert parse_duration("90m") == timedelta(minutes=90)

    def test_days_only(self):
        assert parse_duration("1d") == timedelta(days=1)

    def test_hours_and_minutes(self):
        assert parse_duration("2h30m") == timedelta(hours=2, minutes=30)

    def test_full_spec(self):
        assert parse_duration("1d2h3m4s") == timedelta(days=1, hours=2, minutes=3, seconds=4)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_duration("")

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("xyz")


class TestGetExpirationTime:
    def test_string_duration(self):
        start = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = get_expiration_time("4h", start_time=start)
        assert result == datetime(2025, 1, 1, 16, 0, 0, tzinfo=timezone.utc)

    def test_timedelta_duration(self):
        start = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = get_expiration_time(timedelta(hours=2), start_time=start)
        assert result == datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

    def test_defaults_to_now(self):
        before = datetime.now(timezone.utc)
        result = get_expiration_time("1h")
        after = datetime.now(timezone.utc)
        assert before + timedelta(hours=1) <= result <= after + timedelta(hours=1)


class TestIsExpired:
    def test_past_time_is_expired(self):
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert is_expired(past) is True

    def test_future_time_is_not_expired(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        assert is_expired(future) is False


class TestTimeUntilExpiration:
    def test_future_expiration_is_positive(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        remaining = time_until_expiration(future)
        assert remaining > timedelta(0)

    def test_past_expiration_is_negative(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        remaining = time_until_expiration(past)
        assert remaining < timedelta(0)
