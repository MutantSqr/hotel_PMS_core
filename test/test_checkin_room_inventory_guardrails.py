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
    return assistant, room, reservation


def test_check_in_rejects_showroom():
    assistant, room, reservation = make_system()
    room.showroom = True

    with pytest.raises(ValueError, match="showroom"):
        assistant.check_in_guest(reservation.reservation_id, "Alice")


def test_check_in_rejects_out_of_service_room():
    assistant, room, reservation = make_system()
    room.occupancy_status = "out_of_service"

    with pytest.raises(ValueError, match="out of service"):
        assistant.check_in_guest(reservation.reservation_id, "Alice")
