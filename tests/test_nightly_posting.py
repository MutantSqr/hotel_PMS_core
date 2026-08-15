from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.folio import Folio
from app.nightly_posting import NightlyPostingService


def make_reservation(check_in=datetime(2026, 8, 11, 15, 0), checked_in=True):
    return SimpleNamespace(
        reservation_id="RES001",
        check_in_date=check_in,
        check_out_date=datetime(2026, 8, 13, 11, 0),
        expected_daily_rate=200.0,
        status="confirmed",
        checked_in=checked_in,
    )


def make_folio():
    return Folio("FOL001", "RES001", "Alice", 1501)


def test_posts_one_room_night_and_tax():
    reservation = make_reservation()
    folio = make_folio()

    result = NightlyPostingService.post_room_night(
        reservation, folio, datetime(2026, 8, 12, 2, 45), 0.10
    )

    assert result["room_charge"] == Decimal("200.00")
    assert result["tax_charge"] == Decimal("20.00")
    assert folio.total_charges == Decimal("220.00")
    assert folio.balance == Decimal("220.00")


def test_requires_checked_in_reservation():
    reservation = make_reservation(checked_in=False)
    folio = make_folio()

    with pytest.raises(ValueError, match="Only checked-in"):
        NightlyPostingService.post_room_night(
            reservation, folio, datetime(2026, 8, 12, 2, 45), 0.10
        )


def test_rejects_future_arrival():
    reservation = make_reservation(datetime(2026, 8, 20, 15, 0))
    folio = make_folio()

    with pytest.raises(ValueError, match="before arrival"):
        NightlyPostingService.post_room_night(
            reservation, folio, datetime(2026, 8, 12, 2, 45), 0.10
        )


def test_allows_departure_date_night_audit_before_checkout():
    reservation = make_reservation()
    folio = make_folio()

    result = NightlyPostingService.post_room_night(
        reservation, folio, datetime(2026, 8, 13, 2, 45), 0.10
    )

    assert result["status"] == "success"
    assert folio.total_charges == Decimal("220.00")


def test_rejects_posting_after_departure():
    reservation = make_reservation()
    folio = make_folio()

    with pytest.raises(ValueError, match="after departure"):
        NightlyPostingService.post_room_night(
            reservation, folio, datetime(2026, 8, 13, 11, 1), 0.10
        )


def test_duplicate_room_night_is_rejected_without_extra_charge():
    reservation = make_reservation()
    folio = make_folio()
    audit_time = datetime(2026, 8, 12, 2, 45)

    NightlyPostingService.post_room_night(reservation, folio, audit_time, 0.10)
    with pytest.raises(ValueError, match="already been posted"):
        NightlyPostingService.post_room_night(reservation, folio, audit_time, 0.10)

    assert len(folio.charges) == 2
    assert folio.total_charges == Decimal("220.00")


def test_negative_tax_rate_is_rejected_before_mutation():
    reservation = make_reservation()
    folio = make_folio()

    with pytest.raises(ValueError, match="Tax rate cannot be negative"):
        NightlyPostingService.post_room_night(
            reservation, folio, datetime(2026, 8, 12, 2, 45), -0.01
        )

    assert folio.total_charges == Decimal("0.00")


def test_invalid_room_rate_is_rejected_before_mutation():
    reservation = make_reservation()
    reservation.expected_daily_rate = 0
    folio = make_folio()

    with pytest.raises(ValueError, match="greater than zero"):
        NightlyPostingService.post_room_night(
            reservation, folio, datetime(2026, 8, 12, 2, 45), 0.10
        )

    assert folio.total_charges == Decimal("0.00")
