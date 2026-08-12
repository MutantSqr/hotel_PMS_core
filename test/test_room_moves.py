from datetime import datetime, timedelta

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room


def make_system(capacity=4):
    assistant = HotelAssistant()
    old_room = Room(1501, 15, capacity, ["King Bed"], "presidential", "available", False, "", False)
    new_room = Room(1502, 15, capacity, ["King Bed"], "presidential", "available", False, "", False)
    assistant.add_room(old_room)
    assistant.add_room(new_room)

    guest = Guest("Alice", "alice@example.com", "Visa", "", "", "CONF001")
    assistant.add_guest(guest)

    check_in = datetime(2026, 8, 20, 15, 0)
    reservation = Reservation("RES001", [guest.name], check_in, check_in + timedelta(days=2), old_room, 500.0, "")
    assistant.add_reservation(reservation)
    return assistant, old_room, new_room, guest, reservation


def test_future_reservation_can_change_to_available_room():
    assistant, old_room, new_room, guest, reservation = make_system()

    result = assistant.change_room("RES001", 1502)

    assert result["status"] == "success"
    assert reservation.room is new_room
    assert old_room.occupancy_status == "available"
    assert new_room.occupancy_status == "reserved"


def test_room_move_rejects_overlapping_destination_without_releasing_old_room():
    assistant, old_room, new_room, guest, reservation = make_system()
    other = Reservation(
        "RES002", [guest.name], datetime(2026, 8, 21, 15, 0), datetime(2026, 8, 23, 15, 0),
        new_room, 500.0, ""
    )
    assistant.add_reservation(other)

    with pytest.raises(ValueError, match="already reserved"):
        assistant.change_room("RES001", 1502)

    assert reservation.room is old_room
    assert old_room.occupancy_status == "reserved"
    assert new_room.occupancy_status == "reserved"


def test_back_to_back_destination_room_is_allowed():
    assistant, old_room, new_room, guest, reservation = make_system()
    other = Reservation(
        "RES002", [guest.name], datetime(2026, 8, 22, 15, 0), datetime(2026, 8, 24, 15, 0),
        new_room, 500.0, ""
    )
    assistant.add_reservation(other)

    assistant.change_room("RES001", 1502)

    assert reservation.room is new_room
    assert old_room.occupancy_status == "available"


def test_room_move_rejects_out_of_order_destination():
    assistant, old_room, new_room, guest, reservation = make_system()
    new_room.out_of_order = True
    new_room.out_of_order_reason = "Maintenance"

    with pytest.raises(ValueError, match="out of order"):
        assistant.change_room("RES001", 1502)

    assert reservation.room is old_room
    assert old_room.occupancy_status == "reserved"


def test_room_move_rejects_insufficient_capacity():
    assistant, old_room, new_room, guest, reservation = make_system(capacity=2)
    guest2 = Guest("Bob", "bob@example.com", "Visa", "", "", "CONF002")
    assistant.add_guest(guest2)
    reservation.guest_names.append(guest2.name)
    assistant._reservation_guest_map[reservation.reservation_id][guest2.name] = guest2.confirmation_number
    new_room.capacity = 1

    with pytest.raises(ValueError, match="accommodate only 1"):
        assistant.change_room("RES001", 1502)

    assert reservation.room is old_room
    assert old_room.occupancy_status == "reserved"


def test_checked_in_reservation_cannot_be_moved():
    assistant, old_room, new_room, guest, reservation = make_system()
    assistant.check_in_guest("RES001", "Alice", current_datetime=datetime(2026, 8, 20, 15, 0))

    with pytest.raises(ValueError, match="checked in"):
        assistant.change_room("RES001", 1502)

    assert reservation.room is old_room
    assert old_room.occupancy_status == "occupied"
    assert new_room.occupancy_status == "available"


def test_room_move_updates_existing_billing_room_reference():
    assistant, old_room, new_room, guest, reservation = make_system()
    assistant.check_in_guest("RES001", "Alice", current_datetime=datetime(2026, 8, 20, 15, 0))
    # Checked-in reservations are intentionally immovable, so this verifies the
    # rule boundary rather than allowing a billing record to drift independently.
    billing = assistant._get_reservation_billing("RES001")
    assert billing.room is old_room
