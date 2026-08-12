from datetime import datetime
from decimal import Decimal

import pytest

from app.folio import Folio
from app.models import Reservation, Room
from app.night_audit import NightAuditService


def make_reservation(check_in_date):
    room = Room(1501, 15, 2, ["King Bed"], "standard", "available", False, "", False)
    return Reservation(
        "RES001",
        ["Alice"],
        check_in_date,
        check_in_date.replace(day=check_in_date.day + 2),
        room,
        200.0,
        "",
    )


def make_folio():
    return Folio("FOL001", "RES001", "Alice", 1501)


def test_no_show_cannot_process_before_230_am_cutoff():
    reservation = make_reservation(datetime(2026, 8, 11, 15, 0))
    folio = make_folio()
    with pytest.raises(ValueError, match="not eligible"):
        NightAuditService.process_no_show(
            reservation, folio, datetime(2026, 8, 12, 2, 29), 0.10
        )


def test_no_show_processes_at_230_am_with_one_night_room_and_tax():
    reservation = make_reservation(datetime(2026, 8, 11, 15, 0))
    folio = make_folio()
    result = NightAuditService.process_no_show(
        reservation, folio, datetime(2026, 8, 12, 2, 30), 0.10
    )
    assert reservation.status == "no_show"
    assert result["room_charge"] == Decimal("200.00")
    assert result["tax_charge"] == Decimal("20.00")
    assert folio.total_charges == Decimal("220.00")
    assert folio.balance == Decimal("220.00")


def test_future_arrival_cannot_be_marked_no_show_early():
    reservation = make_reservation(datetime(2026, 8, 20, 15, 0))
    folio = make_folio()
    with pytest.raises(ValueError, match="not eligible"):
        NightAuditService.process_no_show(
            reservation, folio, datetime(2026, 8, 12, 2, 30), 0.10
        )


def test_checked_in_reservation_cannot_be_marked_no_show():
    reservation = make_reservation(datetime(2026, 8, 11, 15, 0))
    reservation.checked_in = True
    folio = make_folio()
    with pytest.raises(ValueError, match="not eligible"):
        NightAuditService.process_no_show(
            reservation, folio, datetime(2026, 8, 12, 2, 30), 0.10
        )


def test_no_show_processing_is_idempotent_guarded_by_folio_charge_id():
    reservation = make_reservation(datetime(2026, 8, 11, 15, 0))
    folio = make_folio()
    audit_time = datetime(2026, 8, 12, 2, 30)
    NightAuditService.process_no_show(reservation, folio, audit_time, 0.10)
    with pytest.raises(ValueError, match="already been processed"):
        NightAuditService.process_no_show(reservation, folio, audit_time, 0.10)


def test_negative_tax_rate_is_rejected():
    reservation = make_reservation(datetime(2026, 8, 11, 15, 0))
    folio = make_folio()
    with pytest.raises(ValueError, match="Tax rate cannot be negative"):
        NightAuditService.process_no_show(
            reservation, folio, datetime(2026, 8, 12, 2, 30), -0.01
        )
