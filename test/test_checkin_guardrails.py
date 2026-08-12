from datetime import datetime

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room


def make_system():
    assistant = HotelAssistant()
    room = Room(1501, 15, 2, ["King Bed"], "standard", "available", False, "", False)
    guest = Guest("Alice", "alice@example.com", "Visa", "", "", "G001")
    assistant.add_room(room)
    assistant.add_guest(guest)
    reservation = Reservation(
        "RES001",
        [guest.name],
        datetime(2026, 8, 11, 15, 0),
        datetime(2026, 8, 13, 15, 0),
        room,
        200.0,
        "",
    )
    assistant.add_reservation(reservation)
    return assistant, room, guest, reservation


def test_check_in_rejects_missing_reservation():
    assistant, *_ = make_system()
    with pytest.raises(ValueError, match="Reservation BAD999 not found"):
        assistant.check_in_guest("BAD999", "Alice")


def test_check_in_rejects_guest_not_on_reservation():
    assistant, room, guest, reservation = make_system()
    other = Guest("Bob", "bob@example.com", "Visa", "", "", "G002")
    assistant.add_guest(other)

    with pytest.raises(ValueError, match="not part of reservation"):
        assistant.check_in_guest(reservation.reservation_id, "Bob")


def test_check_in_rejects_before_arrival():
    assistant, room, guest, reservation = make_system()
    current = datetime(2026, 8, 11, 14, 59)

    with pytest.raises(ValueError, match="not due for check-in"):
        assistant.check_in_guest(reservation.reservation_id, "Alice", current_datetime=current)


def test_check_in_rejects_after_departure():
    assistant, room, guest, reservation = make_system()
    current = datetime(2026, 8, 13, 15, 0)

    with pytest.raises(ValueError, match="passed its check-out date"):
        assistant.check_in_guest(reservation.reservation_id, "Alice", current_datetime=current)


def test_check_in_rejects_out_of_order_room():
    assistant, room, guest, reservation = make_system()
    room.out_of_order = True

    with pytest.raises(ValueError, match="out of order"):
        assistant.check_in_guest(reservation.reservation_id, "Alice")


def test_check_in_rejects_already_occupied_room():
    assistant, room, guest, reservation = make_system()
    room.occupancy_status = "occupied"

    with pytest.raises(ValueError, match="currently occupied"):
        assistant.check_in_guest(reservation.reservation_id, "Alice")


def test_check_in_rejects_duplicate_guest():
    assistant, room, guest, reservation = make_system()
    assistant.check_in_guest(reservation.reservation_id, "Alice")

    with pytest.raises(ValueError, match="already been checked in"):
        assistant.check_in_guest(reservation.reservation_id, "Alice")


def test_check_in_rejects_capacity_overflow():
    assistant, room, guest, reservation = make_system()
    second = Guest("Bob", "bob@example.com", "Visa", "", "", "G002")
    third = Guest("Charlie", "charlie@example.com", "Visa", "", "", "G003")
    assistant.add_guest(second)
    assistant.add_guest(third)
    reservation.guest_names = ["Alice", "Bob", "Charlie"]
    assistant._reservation_guest_map[reservation.reservation_id]["Bob"] = "G002"
    assistant._reservation_guest_map[reservation.reservation_id]["Charlie"] = "G003"

    with pytest.raises(ValueError, match="can accommodate only 2 guests"):
        assistant.check_in_guest(
            reservation.reservation_id,
            "Alice",
            accompanying_guest_names=["Bob", "Charlie"],
        )
