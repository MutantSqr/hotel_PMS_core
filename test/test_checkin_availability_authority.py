from datetime import datetime, timedelta

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room


def build_pms():
    pms = HotelAssistant()
    pms.add_room(Room("1501", "King", 2))
    pms.add_room(Room("1502", "King", 2))
    pms.add_guest(Guest("G001", "Alice Smith"))
    pms.add_guest(Guest("G002", "Bob Smith"))
    return pms


def make_reservation(pms, reservation_id, room_number, guest_name, check_in, check_out):
    reservation = Reservation(
        reservation_id=reservation_id,
        room=pms.rooms[room_number],
        guest_names=[guest_name],
        check_in_date=check_in,
        check_out_date=check_out,
        expected_daily_rate=100,
    )
    pms.add_reservation(reservation)
    return reservation


def test_check_in_rejects_room_already_occupied_by_another_reservation():
    pms = build_pms()
    start = datetime(2026, 8, 12)
    end = start + timedelta(days=2)
    first = make_reservation(pms, "RES001", "1501", "Alice Smith", start, end)
    second = make_reservation(pms, "RES002", "1502", "Bob Smith", start, end)

    pms.check_in_guest(first.reservation_id, "Alice Smith", current_datetime=start)
    second.room = pms.rooms["1501"]

    with pytest.raises(ValueError, match="already occupied"):
        pms.check_in_guest(second.reservation_id, "Bob Smith", current_datetime=start)


def test_check_in_rejects_out_of_service_room():
    pms = build_pms()
    room = pms.rooms["1501"]
    room.set_out_of_service("Maintenance")
    start = datetime(2026, 8, 12)
    end = start + timedelta(days=2)
    reservation = make_reservation(pms, "RES001", "1501", "Alice Smith", start, end)

    with pytest.raises(ValueError, match="not available"):
        pms.check_in_guest(reservation.reservation_id, "Alice Smith", current_datetime=start)
