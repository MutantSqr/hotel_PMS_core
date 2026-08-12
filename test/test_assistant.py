from datetime import datetime, timedelta

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room, Vehicle


def make_system(guest_names=None, rate=450.0, days=2, capacity=4, room_number=1501):
    assistant = HotelAssistant()
    room = Room(room_number, 15, capacity, ["King Bed", "Ocean View"], "presidential", "available", False, "", False)
    guest_names = guest_names or ["Rondrick Bowser"]
    guests = []
    for index, name in enumerate(guest_names, start=1):
        guest = Guest(name, f"guest{index}@example.com", "Visa ending 4242", "Vanguard Fleet", "High floor", f"CONF{index:03d}")
        assistant.add_guest(guest)
        guests.append(guest)
    check_in_date = datetime(2026, 8, 11, 15, 0)
    check_out_date = check_in_date + timedelta(days=days)
    reservation = Reservation("RES999", guest_names, check_in_date, check_out_date, room, rate, "Extra Towels")
    assistant.add_room(room)
    assistant.add_reservation(reservation)
    return assistant, room, guests, reservation


def test_non_overlapping_reservation_same_room_is_allowed():
    assistant, room, guests, reservation = make_system()
    second = Reservation("RES1000", [guests[0].name], datetime(2026, 8, 20, 15, 0), datetime(2026, 8, 22, 15, 0), room, 500.0, "")
    assistant.add_reservation(second)
    assert list(assistant.reservations) == ["RES999", "RES1000"]


def test_overlapping_reservation_same_room_is_rejected():
    assistant, room, guests, reservation = make_system()
    second = Reservation("RES1001", [guests[0].name], datetime(2026, 8, 12, 15, 0), datetime(2026, 8, 15, 15, 0), room, 500.0, "")
    with pytest.raises(ValueError, match="already reserved"):
        assistant.add_reservation(second)


def test_back_to_back_reservation_is_allowed():
    assistant, room, guests, reservation = make_system()
    second = Reservation("RES1002", [guests[0].name], datetime(2026, 8, 13, 15, 0), datetime(2026, 8, 15, 15, 0), room, 500.0, "")
    assistant.add_reservation(second)
    assert "RES1002" in assistant.reservations


def test_cancel_confirmed_reservation_releases_room():
    assistant, room, guests, reservation = make_system()
    result = assistant.cancel_reservation(reservation.reservation_id)
    assert result["status"] == "success"
    assert reservation.status == "cancelled"
    assert room.occupancy_status == "available"


def test_cancelled_reservation_does_not_block_same_dates():
    assistant, room, guests, reservation = make_system()
    assistant.cancel_reservation(reservation.reservation_id)
    replacement = Reservation("RES1003", [guests[0].name], datetime(2026, 8, 11, 15, 0), datetime(2026, 8, 13, 15, 0), room, 500.0, "")
    assistant.add_reservation(replacement)
    assert replacement.status == "confirmed"


def test_cancelled_reservation_cannot_be_checked_in():
    assistant, room, guests, reservation = make_system()
    assistant.cancel_reservation(reservation.reservation_id)
    with pytest.raises(ValueError, match="not eligible for check-in"):
        assistant.check_in_guest(reservation.reservation_id, guests[0].name)


def test_checked_in_reservation_cannot_be_cancelled():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)
    with pytest.raises(ValueError, match="cannot be cancelled"):
        assistant.cancel_reservation(reservation.reservation_id)
    assert reservation.status == "checked_in"
    assert room.occupancy_status == "occupied"


def test_checked_out_reservation_cannot_be_cancelled():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)
    assistant.check_out_guest(reservation.reservation_id, guests[0].name, 900.0)
    with pytest.raises(ValueError, match="cannot be cancelled"):
        assistant.cancel_reservation(reservation.reservation_id)
    assert reservation.status == "checked_out"


def test_cancelled_reservation_cannot_be_cancelled_again():
    assistant, room, guests, reservation = make_system()
    assistant.cancel_reservation(reservation.reservation_id)
    with pytest.raises(ValueError, match="cannot be cancelled"):
        assistant.cancel_reservation(reservation.reservation_id)


def test_cancel_does_not_make_room_available_when_later_reservation_exists():
    assistant, room, guests, reservation = make_system()
    later = Reservation("RES1004", [guests[0].name], datetime(2026, 8, 13, 15, 0), datetime(2026, 8, 15, 15, 0), room, 500.0, "")
    assistant.add_reservation(later)
    result = assistant.cancel_reservation(reservation.reservation_id)
    assert result["room_status"] == "reserved"
    assert room.occupancy_status == "reserved"


def test_normal_check_in_and_paid_checkout():
    assistant, room, guests, reservation = make_system()
    result = assistant.check_in_guest(reservation.reservation_id, guests[0].name)
    assert result["status"] == "success"
    assert result["amount_due"] == 900.0
    assert room.occupancy_status == "occupied"
    result = assistant.check_out_guest(reservation.reservation_id, guests[0].name, 900.0)
    assert result["balance"] == 0
    assert result["credit"] == 0
    assert room.occupancy_status == "available"
    assert reservation.status == "checked_out"


def test_partial_balance_cannot_checkout_without_night_audit_or_pm():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)
    with pytest.raises(ValueError, match="Outstanding balance"):
        assistant.check_out_guest(reservation.reservation_id, guests[0].name, 600.0)
    assert room.occupancy_status == "occupied"
    assert reservation.checked_out is False


def test_night_audit_can_settle_remaining_balance():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)
    result = assistant.check_out_guest(reservation.reservation_id, guests[0].name, amount_paid=600.0, night_audit=True)
    assert result["amount_paid"] == 900.0
    assert result["balance"] == 0
    assert result["pm_account"] is False
    assert room.occupancy_status == "available"


def test_outstanding_balance_can_transfer_to_pm_account():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)
    result = assistant.check_out_guest(reservation.reservation_id, guests[0].name, amount_paid=600.0, transfer_to_pm=True)
    assert result["balance"] == 300.0
    assert result["pm_account"] is True
    assert assistant.pm_accounts[result["billing_id"]] == 300.0
    assert room.occupancy_status == "available"


def test_overpayment_creates_credit_and_allows_checkout():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)
    result = assistant.check_out_guest(reservation.reservation_id, guests[0].name, 1000.0)
    assert result["balance"] == -100.0
    assert result["credit"] == 100.0
    assert room.occupancy_status == "available"


def test_no_show_at_230_am_charges_one_night_plus_tax_and_releases_room():
    assistant, room, guests, reservation = make_system(rate=450.0, days=2)
    result = assistant.run_night_audit(datetime(2026, 8, 12, 2, 30), 0.15)
    assert len(result) == 1
    assert result[0]["status"] == "no_show"
    assert result[0]["room_charge"] == 450.0
    assert result[0]["tax_amount"] == 67.5
    assert result[0]["amount_due"] == 517.5
    assert reservation.status == "no_show"
    assert room.occupancy_status == "available"


def test_no_show_billing_ledger_contains_exactly_one_charge():
    assistant, room, guests, reservation = make_system(rate=450.0, days=4)
    result = assistant.run_night_audit(datetime(2026, 8, 12, 2, 30), 0.15)
    billing = assistant.billing_records[result[0]["billing_id"]]
    assert billing.amount_due == 517.5
    assert billing.amount_paid == 0
    assert billing.tax_amount == 67.5
    assert billing.payment_method == "No-Show Charge"
    assert len(assistant.billing_records) == 1


def test_no_show_is_idempotent_and_cannot_charge_twice():
    assistant, room, guests, reservation = make_system(rate=450.0, days=4)
    first = assistant.run_night_audit(datetime(2026, 8, 12, 2, 30), 0.15)
    second = assistant.run_night_audit(datetime(2026, 8, 12, 2, 31), 0.15)
    assert len(first) == 1
    assert second == []
    assert len(assistant.billing_records) == 1


def test_no_show_rejects_invalid_tax_rate():
    assistant, room, guests, reservation = make_system()
    with pytest.raises(ValueError, match="Tax rate must be between 0 and 1"):
        assistant.run_night_audit(datetime(2026, 8, 12, 2, 30), 1.01)


def test_no_show_vehicle_is_removed_from_vehicle_registry():
    assistant, room, guests, reservation = make_system()
    vehicle = Vehicle("VEHNS", "TX-9900", "Buick", "Enclave", "Black", guests[0].name, room, reservation)
    room.vehicle = vehicle
    assistant.vehicles[vehicle.vehicle_id] = vehicle
    result = assistant.run_night_audit(datetime(2026, 8, 12, 2, 30), 0.15)
    assert result[0]["vehicle_removed"] == "VEHNS"
    assert "VEHNS" not in assistant.vehicles
    assert room.vehicle is None


def test_duplicate_check_in_is_rejected():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)
    with pytest.raises(ValueError, match="already been checked in"):
        assistant.check_in_guest(reservation.reservation_id, guests[0].name)


def test_vehicle_is_removed_on_checkout():
    assistant, room, guests, reservation = make_system()
    vehicle = Vehicle("VEH01", "TX-8890", "Buick", "Enclave", "Black", guests[0].name, room, reservation)
    assistant.check_in_guest(reservation.reservation_id, guests[0].name, vehicle=vehicle)
    result = assistant.check_out_guest(reservation.reservation_id, guests[0].name, 900.0)
    assert "VEH01" not in assistant.vehicles
    assert room.vehicle is None
    assert result["vehicle_removed"] == "VEH01"


def test_presidential_suite_cannot_be_double_assigned_by_overlap():
    assistant, room, guests, reservation = make_system(room_number=1501)
    second_guest = Guest("Second Guest", "second@example.com", "Visa ending 5555", "", "", "CONF002")
    assistant.add_guest(second_guest)
    second = Reservation("PRES002", [second_guest.name], datetime(2026, 8, 11, 16, 0), datetime(2026, 8, 12, 16, 0), room, 900.0, "")
    with pytest.raises(ValueError, match="already reserved"):
        assistant.add_reservation(second)


def test_presidential_suite_allows_back_to_back_assignment():
    assistant, room, guests, reservation = make_system(room_number=1501)
    second = Reservation("PRES003", [guests[0].name], datetime(2026, 8, 13, 15, 0), datetime(2026, 8, 14, 15, 0), room, 900.0, "")
    assistant.add_reservation(second)
    assert second.status == "confirmed"


def test_early_arrival_is_rejected_without_explicit_early_check_in():
    assistant, room, guests, reservation = make_system()
    with pytest.raises(ValueError, match="not due for check-in"):
        assistant.check_in_guest(reservation.reservation_id, guests[0].name, current_datetime=datetime(2026, 8, 11, 14, 59))


def test_check_in_allows_multiple_registered_guests_within_capacity():
    assistant, room, guests, reservation = make_system(guest_names=["Guest One", "Guest Two"])
    result = assistant.check_in_guest(reservation.reservation_id, guests[0].name, accompanying_guest_names=[guests[1].name])
    assert result["guests"] == ["Guest One", "Guest Two"]
    assert room.current_guests == ["Guest One", "Guest Two"]
    assert room.occupancy_status == "occupied"


def test_multiple_guest_check_in_rejects_capacity_overflow():
    assistant, room, guests, reservation = make_system(guest_names=["A", "B", "C", "D"], capacity=4)
    with pytest.raises(ValueError, match="accommodate only 4"):
        assistant.check_in_guest(reservation.reservation_id, guests[0].name, accompanying_guest_names=guests[1:] + ["Unauthorized Fifth Guest"])


def test_corrupt_available_room_cannot_hide_another_checked_in_reservation():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)
    room.occupancy_status = "available"
    future_guest = Guest("Future Guest", "future@example.com", "Visa ending 7777", "", "", "CONF002")
    assistant.add_guest(future_guest)
    future = Reservation("CORRUPT2", [future_guest.name], datetime(2026, 8, 11, 15, 30), datetime(2026, 8, 12, 15, 30), room, 500.0, "")
    assistant.reservations[future.reservation_id] = future
    assistant._reservation_guest_map[future.reservation_id] = {future_guest.name: future_guest.confirmation_number}
    with pytest.raises(ValueError, match="already occupied"):
        assistant.check_in_guest(future.reservation_id, future_guest.name, current_datetime=datetime(2026, 8, 11, 16, 0))


def test_checkout_keeps_room_reserved_for_future_back_to_back_guest():
    assistant, room, guests, reservation = make_system()
    later = Reservation("FUTURE01", [guests[0].name], datetime(2026, 8, 13, 15, 0), datetime(2026, 8, 15, 15, 0), room, 500.0, "")
    assistant.add_reservation(later)
    assistant.check_in_guest(reservation.reservation_id, guests[0].name, current_datetime=datetime(2026, 8, 11, 15, 0))
    assistant.check_out_guest(reservation.reservation_id, guests[0].name, 900.0)
    assert room.occupancy_status == "reserved"


def test_no_show_keeps_room_reserved_when_future_reservation_exists():
    assistant, room, guests, reservation = make_system()
    later = Reservation("FUTURE02", [guests[0].name], datetime(2026, 8, 13, 15, 0), datetime(2026, 8, 15, 15, 0), room, 500.0, "")
    assistant.add_reservation(later)
    assistant.run_night_audit(datetime(2026, 8, 12, 2, 30), 0.15)
    assert reservation.status == "no_show"
    assert room.occupancy_status == "reserved"
