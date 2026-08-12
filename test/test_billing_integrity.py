from datetime import datetime, timedelta

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room


def make_checked_in_system():
    assistant = HotelAssistant()
    room = Room(1501, 15, 4, ["King Bed"], "presidential", "available", False, "", False)
    guest = Guest("Billing Guest", "billing@example.com", "Visa ending 4242", "", "", "BILLGUEST")
    assistant.add_guest(guest)
    assistant.add_room(room)
    start = datetime(2026, 8, 11, 15, 0)
    end = start + timedelta(days=2)
    reservation = Reservation("BILLRES", [guest.name], start, end, room, 450.0, "")
    assistant.add_reservation(reservation)
    assistant.check_in_guest(reservation.reservation_id, guest.name, current_datetime=start)
    return assistant, room, guest, reservation


def test_duplicate_checkout_cannot_create_second_settlement():
    assistant, room, guest, reservation = make_checked_in_system()
    first = assistant.check_out_guest(reservation.reservation_id, guest.name, 900.0)
    with pytest.raises(ValueError, match="already been checked out"):
        assistant.check_out_guest(reservation.reservation_id, guest.name, 900.0)
    assert len(assistant.billing_records) == 1
    billing = assistant.billing_records[first["billing_id"]]
    assert billing.amount_paid == 900.0
    assert billing.balance == 0


def test_failed_partial_checkout_does_not_record_payment():
    assistant, room, guest, reservation = make_checked_in_system()
    billing = next(iter(assistant.billing_records.values()))
    with pytest.raises(ValueError, match="Outstanding balance"):
        assistant.check_out_guest(reservation.reservation_id, guest.name, 899.99)
    assert billing.amount_paid == 0
    assert billing.balance == 900.0
    assert reservation.checked_out is False
    assert room.occupancy_status == "occupied"


def test_night_audit_settlement_is_single_use():
    assistant, room, guest, reservation = make_checked_in_system()
    first = assistant.check_out_guest(reservation.reservation_id, guest.name, 600.0, night_audit=True)
    with pytest.raises(ValueError, match="already been checked out"):
        assistant.check_out_guest(reservation.reservation_id, guest.name, 300.0, night_audit=True)
    billing = assistant.billing_records[first["billing_id"]]
    assert billing.amount_paid == 900.0
    assert billing.balance == 0
    assert len(assistant.billing_records) == 1


def test_pm_transfer_does_not_turn_unpaid_balance_into_a_payment():
    assistant, room, guest, reservation = make_checked_in_system()
    result = assistant.check_out_guest(reservation.reservation_id, guest.name, 600.0, transfer_to_pm=True)
    billing = assistant.billing_records[result["billing_id"]]
    assert billing.amount_due == 900.0
    assert billing.amount_paid == 600.0
    assert billing.balance == 300.0
    assert billing.pm_account is True
    assert assistant.pm_accounts[result["billing_id"]] == 300.0


def test_overpayment_is_recorded_once_as_credit():
    assistant, room, guest, reservation = make_checked_in_system()
    result = assistant.check_out_guest(reservation.reservation_id, guest.name, 1000.0)
    billing = assistant.billing_records[result["billing_id"]]
    assert billing.amount_paid == 1000.0
    assert billing.balance == -100.0
    assert billing.credit == 100.0
    assert len(assistant.billing_records) == 1


def test_no_show_night_audit_is_idempotent():
    assistant = HotelAssistant()
    room = Room(1501, 15, 4, ["King Bed"], "presidential", "available", False, "", False)
    guest = Guest("No Show Guest", "noshow@example.com", "Visa ending 4242", "", "", "NOSHOWGUEST")
    assistant.add_guest(guest)
    assistant.add_room(room)
    start = datetime(2026, 8, 11, 15, 0)
    reservation = Reservation("NOSHOWRES", [guest.name], start, start + timedelta(days=3), room, 450.0, "")
    assistant.add_reservation(reservation)

    first = assistant.run_night_audit(datetime(2026, 8, 12, 2, 30), 0.15)
    second = assistant.run_night_audit(datetime(2026, 8, 12, 2, 31), 0.15)

    assert len(first) == 1
    assert second == []
    assert len(assistant.billing_records) == 1
    billing = assistant.billing_records[first[0]["billing_id"]]
    assert billing.amount_due == 517.50
    assert billing.tax_amount == 67.50
    assert billing.amount_paid == 0
