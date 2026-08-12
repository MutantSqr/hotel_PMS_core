from datetime import datetime, timedelta

from app.assist import HotelAssistant
from app.models import Room


def test_room_move_rejects_showroom_destination():
    assistant = HotelAssistant()
    old_room = Room(1501, 15, 2, [], "standard", "available", False, "", False)
    showroom = Room(1502, 15, 2, [], "standard", "available", False, "", True)
    assistant.add_room(old_room)
    assistant.add_room(showroom)

    from app.models import Guest, Reservation
    guest = Guest("Alice", "alice@example.com", "Visa", "", "", "CONF001")
    assistant.add_guest(guest)
    start = datetime(2026, 8, 20, 15, 0)
    reservation = Reservation("RES001", [guest.name], start, start + timedelta(days=2), old_room, 100, "")
    assistant.add_reservation(reservation)

    try:
        assistant.change_room("RES001", 1502)
        assert False, "Expected showroom destination to be rejected"
    except ValueError as exc:
        assert "not available" in str(exc)
    assert reservation.room is old_room


def test_room_move_rejects_out_of_service_destination():
    assistant = HotelAssistant()
    old_room = Room(1501, 15, 2, [], "standard", "available", False, "", False)
    oos_room = Room(1502, 15, 2, [], "standard", "out_of_service", False, "Maintenance", False)
    assistant.add_room(old_room)
    assistant.add_room(oos_room)

    from app.models import Guest, Reservation
    guest = Guest("Alice", "alice@example.com", "Visa", "", "", "CONF001")
    assistant.add_guest(guest)
    start = datetime(2026, 8, 20, 15, 0)
    reservation = Reservation("RES001", [guest.name], start, start + timedelta(days=2), old_room, 100, "")
    assistant.add_reservation(reservation)

    try:
        assistant.change_room("RES001", 1502)
        assert False, "Expected out-of-service destination to be rejected"
    except ValueError as exc:
        assert "not available" in str(exc)
    assert reservation.room is old_room
