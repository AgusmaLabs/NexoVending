from datetime import UTC, datetime, timedelta

import pytest

from nexo_vending.domain.identity.errors import InvalidEmailError, InvalidValidityPeriodError
from nexo_vending.domain.identity.value_objects import Email, ValidityPeriod


def test_email_normalizes_case() -> None:
    assert Email("User@Example.COM").value == "user@example.com"


def test_email_trims_whitespace() -> None:
    assert Email("  user@example.com  ").value == "user@example.com"


def test_email_rejects_empty() -> None:
    with pytest.raises(InvalidEmailError):
        Email("   ")


def test_email_rejects_invalid_format() -> None:
    with pytest.raises(InvalidEmailError):
        Email("not-an-email")


def test_validity_period_accepts_open_end() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    period = ValidityPeriod(valid_from=start, valid_until=None)
    assert period.is_valid_at(start)


def test_validity_period_accepts_valid_range() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)
    ValidityPeriod(valid_from=start, valid_until=end)


def test_validity_period_rejects_reversed_range() -> None:
    start = datetime(2026, 2, 1, tzinfo=UTC)
    end = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(InvalidValidityPeriodError):
        ValidityPeriod(valid_from=start, valid_until=end)


def test_validity_period_is_valid_inside_range() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)
    period = ValidityPeriod(valid_from=start, valid_until=end)
    assert period.is_valid_at(start + timedelta(days=10))


def test_validity_period_is_invalid_before_start() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    period = ValidityPeriod(valid_from=start, valid_until=None)
    assert not period.is_valid_at(start - timedelta(seconds=1))


def test_validity_period_is_invalid_at_end() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)
    period = ValidityPeriod(valid_from=start, valid_until=end)
    assert not period.is_valid_at(end)
