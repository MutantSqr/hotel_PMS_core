from datetime import datetime, timedelta

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room


def make_pms():
    pms = HotelAssistant()
    pms.add_room(Room(1501, 15, 2, [], "presidential", "available", False, None, False))
    pms.add_guest(Guest("Alice", "555-0100", "card", "", "", "G001"))
    return pms


def make_reservation(reservation_id, start, end, room):
    return Reservation(reservation_id, ["Alice"], start, end, room, 200, "")


def test_add_reservation_uses_central_availability_for_overlap():
    pms = make_pms()
    start = datetime(2026, 8, 11)
    first = make_reservation("RES001", start, start + timedelta(days=2), pms.rooms[1501])
    second = make_reservation("RES002", start + timedelta(days=1), start + timedelta(days=3), pms.rooms[1501])

    pms.add_reservation(first)

    with pytest.raises(ValueError, match="already reserved"):
        pms.add_reservation(second)


def test_add_reservation_allows_back_to_back_stays():
    pms = make_pms()
    start = datetime(2026, 8, 11)
    first = make_reservation("RES001", start, start + timedelta(days=2), pms.rooms[1501])
    second = make_reservation("RES002", start + timedelta(days=2), start + timedelta(days=4), pms.rooms[1501])

    pms.add_reservation(first)
    pms.add_reservation(second)

    assert list(pms.reservations) == ["RES001", "RES002"]


def test_add_reservation_rejects_showroom_through_availability_engine():
    pms = make_pms()
    pms.rooms[1501].showroom = True
    start = datetime(2026, 8, 11)
    reservation = make_reservation("RES001", start, start + timedelta(days=1), pms.rooms[1501])

    with pytest.raises(ValueError, match="not available"):
        pms.add_reservation(reservation)


def test_add_reservation_rejects_out_of_service_room_through_availability_engine():
    pms = make_pms()
    pms.rooms[1501].occupancy_status = "out_of_service"
    start = datetime(2026, 8, 11)
    reservation = make_reservation("RES001", start, start + timedelta(days=1), pms.rooms[1501])

    with pytest.raises(ValueError, match="not available"):
        pms.add_reservation(reservation)
