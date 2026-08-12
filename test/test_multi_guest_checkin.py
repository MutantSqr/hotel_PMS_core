from datetime import datetime, timedelta

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room


def make_multi_guest_system():
    assistant = HotelAssistant()
    room = Room(1501, 15, 4, ["King Bed"], "presidential", "available", False, "", False)
    guests = []
    for index, name in enumerate(["Alice", "Bob", "Charlie"], start=1):
        guest = Guest(name, f"{name.lower()}@example.com", "Visa", "", "", f"MG{index:03d}")
        assistant.add_guest(guest)
        guests.append(guest)
    reservation = Reservation(
        "MULTI001",
        [guest.name for guest in guests],
        datetime(2026, 8, 11, 15, 0),
        datetime(2026, 8, 13, 15, 0),
        room,
        900.0,
        "",
    )
    assistant.add_room(room)
    assistant.add_reservation(reservation)
    return assistant, room, guests, reservation


def test_registered_guests_can_check_in_separately():
    assistant, room, guests, reservation = make_multi_guest_system()

    first = assistant.check_in_guest(reservation.reservation_id, "Alice")
    second = assistant.check_in_guest(reservation.reservation_id, "Bob")

    assert first["guests"] == ["Alice"]
    assert second["guests"] == ["Alice", "Bob"]
    assert reservation.checked_in is True
    assert reservation.checked_in_guest_names == ["Alice", "Bob"]
    assert room.current_guests == ["Alice", "Bob"]
    assert room.occupancy_status == "occupied"
    assert len(assistant.billing_records) == 1


def test_guest_cannot_check_in_twice():
    assistant, room, guests, reservation = make_multi_guest_system()
    assistant.check_in_guest(reservation.reservation_id, "Alice")

    with pytest.raises(ValueError, match="already been checked in"):
        assistant.check_in_guest(reservation.reservation_id, "Alice")


def test_first_guest_can_depart_without_releasing_room():
    assistant, room, guests, reservation = make_multi_guest_system()
    assistant.check_in_guest(reservation.reservation_id, "Alice")
    assistant.check_in_guest(reservation.reservation_id, "Bob")

    result = assistant.check_out_guest(reservation.reservation_id, "Alice")

    assert result["status"] == "success"
    assert result["guests_remaining"] == ["Bob"]
    assert reservation.checked_out is False
    assert reservation.status == "checked_in"
    assert reservation.checked_in_guest_names == ["Bob"]
    assert room.current_guests == ["Bob"]
    assert room.occupancy_status == "occupied"


def test_room_cannot_be_financially_checked_out_while_another_guest_remains():
    assistant, room, guests, reservation = make_multi_guest_system()
    assistant.check_in_guest(reservation.reservation_id, "Alice")
    assistant.check_in_guest(reservation.reservation_id, "Bob")

    with pytest.raises(ValueError, match="other registered guests remain"):
        assistant.check_out_guest(reservation.reservation_id, "Alice", amount_paid=900.0)

    assert room.occupancy_status == "occupied"
    assert reservation.checked_in_guest_names == ["Alice", "Bob"]


def test_last_registered_guest_can_complete_room_checkout():
    assistant, room, guests, reservation = make_multi_guest_system()
    assistant.check_in_guest(reservation.reservation_id, "Alice")
    assistant.check_in_guest(reservation.reservation_id, "Bob")
    assistant.check_out_guest(reservation.reservation_id, "Alice")

    result = assistant.check_out_guest(reservation.reservation_id, "Bob", amount_paid=1800.0)

    assert result["balance"] == 0
    assert reservation.checked_in_guest_names == []
    assert reservation.checked_out is True
    assert reservation.status == "checked_out"
    assert room.current_guests == []
    assert room.occupancy_status == "available"


def test_second_guest_does_not_create_duplicate_room_charge():
    assistant, room, guests, reservation = make_multi_guest_system()
    assistant.check_in_guest(reservation.reservation_id, "Alice")
    assistant.check_in_guest(reservation.reservation_id, "Bob")

    assert len(assistant.billing_records) == 1
    billing = next(iter(assistant.billing_records.values()))
    assert billing.amount_due == 1800.0
