from datetime import datetime, timedelta

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room, Vehicle


def make_system(guest_names=None, rate=450.0, days=2, capacity=4):
    assistant = HotelAssistant()
    room = Room(
        1501,
        15,
        capacity,
        ["King Bed", "Ocean View"],
        "presidential",
        "available",
        False,
        "",
        False,
    )

    guest_names = guest_names or ["Rondrick Bowser"]
    guests = []
    for index, name in enumerate(guest_names, start=1):
        guest = Guest(
            name,
            f"guest{index}@example.com",
            "Visa ending 4242",
            "Vanguard Fleet",
            "High floor",
            f"CONF{index:03d}",
        )
        assistant.add_guest(guest)
        guests.append(guest)

    check_in_date = datetime(2026, 8, 11, 15, 0)
    check_out_date = check_in_date + timedelta(days=days)
    reservation = Reservation(
        "RES999",
        guest_names,
        check_in_date,
        check_out_date,
        room,
        rate,
        "Extra Towels",
    )

    assistant.add_room(room)
    assistant.add_reservation(reservation)
    return assistant, room, guests, reservation


def test_normal_reservation_check_in_and_checkout():
    assistant, room, guests, reservation = make_system()

    assert room.occupancy_status == "reserved"

    result = assistant.check_in_guest(reservation.reservation_id, guests[0].name)

    assert result["status"] == "success"
    assert room.occupancy_status == "occupied"
    assert room.current_guest == guests[0].name
    assert room.current_guests == [guests[0].name]
    assert reservation.checked_in is True
    assert result["amount_due"] == 900.0

    result = assistant.check_out_guest(reservation.reservation_id, guests[0].name, 900.0)

    assert result["status"] == "success"
    assert result["balance"] == 0
    assert room.occupancy_status == "available"
    assert room.current_guest is None
    assert reservation.checked_out is True


def test_two_reservations_cannot_claim_same_room():
    assistant, room, guests, reservation = make_system()

    second_reservation = Reservation(
        "RES1000",
        [guests[0].name],
        datetime(2026, 8, 12, 15, 0),
        datetime(2026, 8, 14, 15, 0),
        room,
        500.0,
        "",
    )

    with pytest.raises(ValueError, match="unavailable|active reservation"):
        assistant.add_reservation(second_reservation)

    assert list(assistant.reservations) == ["RES999"]
    assert room.occupancy_status == "reserved"


def test_out_of_order_reservation_does_not_change_state():
    assistant = HotelAssistant()
    room = Room(1502, 15, 2, [], "presidential", "available", True, "Maintenance", False)
    guest = Guest("Guest One", "one@example.com", "Visa", "", "", "CONF001")
    assistant.add_room(room)
    assistant.add_guest(guest)

    reservation = Reservation(
        "RES1001",
        [guest.name],
        datetime(2026, 8, 11, 15, 0),
        datetime(2026, 8, 12, 15, 0),
        room,
        300.0,
        "",
    )

    with pytest.raises(ValueError, match="out of order"):
        assistant.add_reservation(reservation)

    assert "RES1001" not in assistant.reservations
    assert room.occupancy_status == "available"


def test_accompanying_guests_can_check_in_on_one_reservation():
    assistant, room, guests, reservation = make_system(
        guest_names=["Primary Guest", "Accompanying Guest"]
    )

    result = assistant.check_in_guest(
        reservation.reservation_id,
        guests[0].name,
        accompanying_guest_names=[guests[1].name],
    )

    assert result["guests"] == [guests[0].name, guests[1].name]
    assert room.current_guest == guests[0].name
    assert room.current_guests == [guests[0].name, guests[1].name]


def test_room_capacity_rejects_too_many_guests():
    with pytest.raises(ValueError, match="can accommodate only"):
        make_system(
            guest_names=["One", "Two", "Three"],
            capacity=2,
        )


def test_fractional_stay_and_fractional_rate():
    assistant, room, guests, reservation = make_system(rate=125.50, days=1.5)

    assert reservation.calculate_length_of_stay() == 1.5
    assert reservation.calculate_total_expected_bill() == 188.25

    result = assistant.check_in_guest(reservation.reservation_id, guests[0].name)
    assert result["amount_due"] == 188.25


def test_partial_balance_cannot_checkout_without_night_audit_or_pm_account():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)

    with pytest.raises(ValueError, match="Outstanding balance"):
        assistant.check_out_guest(reservation.reservation_id, guests[0].name, 600.0)

    assert room.occupancy_status == "occupied"
    assert reservation.checked_out is False


def test_night_audit_can_settle_remaining_balance():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)

    result = assistant.check_out_guest(
        reservation.reservation_id,
        guests[0].name,
        amount_paid=600.0,
        night_audit=True,
    )

    assert result["balance"] == 0
    assert result["amount_paid"] == 900.0
    assert result["pm_account"] is False
    assert room.occupancy_status == "available"


def test_outstanding_balance_can_transfer_to_pm_account():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)

    result = assistant.check_out_guest(
        reservation.reservation_id,
        guests[0].name,
        amount_paid=600.0,
        transfer_to_pm=True,
    )

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


def test_duplicate_check_in_is_rejected():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)

    with pytest.raises(ValueError, match="already been checked in"):
        assistant.check_in_guest(reservation.reservation_id, guests[0].name)


def test_duplicate_checkout_is_rejected():
    assistant, room, guests, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, guests[0].name)
    assistant.check_out_guest(reservation.reservation_id, guests[0].name, 900.0)

    with pytest.raises(ValueError, match="already been checked out"):
        assistant.check_out_guest(reservation.reservation_id, guests[0].name, 900.0)


def test_vehicle_is_registered_and_removed_on_checkout():
    assistant, room, guests, reservation = make_system()
    vehicle = Vehicle(
        "VEH01",
        "TX-8890",
        "Buick",
        "Enclave",
        "Black",
        guests[0].name,
        room,
        reservation,
    )

    assistant.check_in_guest(reservation.reservation_id, guests[0].name, vehicle=vehicle)

    assert "VEH01" in assistant.vehicles
    assert room.vehicle is vehicle

    result = assistant.check_out_guest(reservation.reservation_id, guests[0].name, 900.0)

    assert "VEH01" not in assistant.vehicles
    assert room.vehicle is None
    assert result["vehicle_removed"] == "VEH01"
