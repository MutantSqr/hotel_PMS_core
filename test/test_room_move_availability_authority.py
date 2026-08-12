from datetime import datetime, timedelta

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room


def make_system(destination_status="available", showroom=False):
    assistant = HotelAssistant()
    old_room = Room(1501, 15, 2, [], "standard", "available", False, "", False)
    reason = "Maintenance" if destination_status == "out_of_service" else ""
    destination = Room(1502, 15, 2, [], "standard", destination_status, False, reason, showroom)
    assistant.add_room(old_room)
    assistant.add_room(destination)
    guest = Guest("Alice", "alice@example.com", "Visa", "", "", "CONF001")
    assistant.add_guest(guest)
    start = datetime(2026, 8, 20, 15, 0)
    reservation = Reservation("RES001", [guest.name], start, start + timedelta(days=2), old_room, 100, "")
    assistant.add_reservation(reservation)
    return assistant, old_room, destination, reservation


def test_room_move_rejects_showroom_destination():
    assistant, old_room, destination, reservation = make_system(showroom=True)

    with pytest.raises(ValueError, match="not available"):
        assistant.change_room("RES001", destination.room_number)

    assert reservation.room is old_room
    assert old_room.occupancy_status == "reserved"


def test_room_move_rejects_out_of_service_destination():
    assistant, old_room, destination, reservation = make_system(destination_status="out_of_service")

    with pytest.raises(ValueError, match="not available"):
        assistant.change_room("RES001", destination.room_number)

    assert reservation.room is old_room
    assert old_room.occupancy_status == "reserved"
