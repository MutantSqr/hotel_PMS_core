from datetime import datetime, timedelta

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room
from app.availability import get_available_rooms, is_room_available


BASE = datetime(2026, 8, 20, 15, 0)


def make_room(number=1501, room_type="standard", status="available", showroom=False, out_of_order=False):
    return Room(number, 15, 2, [], room_type, status, "HVAC failure" if out_of_order else None, showroom)


def add_guest(pms, name="Alice", confirmation="C001"):
    pms.add_guest(Guest(name, "555-0100", "card", None, "", confirmation))


def add_reservation(pms, reservation_id, room, start, end, status="confirmed"):
    reservation = Reservation(reservation_id, ["Alice"], start, end, room, 100, "")
    reservation.status = status
    pms.reservations[reservation_id] = reservation
    return reservation


def test_same_date_range_is_unavailable():
    pms = HotelAssistant()
    room = make_room()
    pms.add_room(room)
    add_reservation(pms, "RES001", room, BASE, BASE + timedelta(days=2))

    assert is_room_available(pms, 1501, BASE, BASE + timedelta(days=2)) is False


def test_overlapping_date_range_is_unavailable():
    pms = HotelAssistant()
    room = make_room()
    pms.add_room(room)
    add_reservation(pms, "RES001", room, BASE, BASE + timedelta(days=2))

    assert is_room_available(pms, 1501, BASE + timedelta(days=1), BASE + timedelta(days=3)) is False


def test_back_to_back_reservation_is_allowed():
    pms = HotelAssistant()
    room = make_room()
    pms.add_room(room)
    add_reservation(pms, "RES001", room, BASE, BASE + timedelta(days=2))

    assert is_room_available(pms, 1501, BASE + timedelta(days=2), BASE + timedelta(days=4)) is True


def test_cancelled_reservation_does_not_block_inventory():
    pms = HotelAssistant()
    room = make_room()
    pms.add_room(room)
    add_reservation(pms, "RES001", room, BASE, BASE + timedelta(days=2), status="cancelled")

    assert is_room_available(pms, 1501, BASE, BASE + timedelta(days=2)) is True


def test_no_show_does_not_block_inventory():
    pms = HotelAssistant()
    room = make_room()
    pms.add_room(room)
    add_reservation(pms, "RES001", room, BASE, BASE + timedelta(days=2), status="no_show")

    assert is_room_available(pms, 1501, BASE, BASE + timedelta(days=2)) is True


def test_showroom_is_unavailable():
    pms = HotelAssistant()
    pms.add_room(make_room(showroom=True))

    assert is_room_available(pms, 1501, BASE, BASE + timedelta(days=1)) is False


def test_out_of_order_is_unavailable():
    pms = HotelAssistant()
    pms.add_room(make_room(out_of_order=True))

    assert is_room_available(pms, 1501, BASE, BASE + timedelta(days=1)) is False


def test_out_of_service_is_unavailable():
    pms = HotelAssistant()
    pms.add_room(make_room(status="out_of_service"))

    assert is_room_available(pms, 1501, BASE, BASE + timedelta(days=1)) is False


def test_occupied_room_is_unavailable():
    pms = HotelAssistant()
    pms.add_room(make_room(status="occupied"))

    assert is_room_available(pms, 1501, BASE, BASE + timedelta(days=1)) is False


def test_excluding_current_reservation_allows_self_check():
    pms = HotelAssistant()
    room = make_room()
    pms.add_room(room)
    reservation = add_reservation(pms, "RES001", room, BASE, BASE + timedelta(days=2))

    assert is_room_available(
        pms, 1501, BASE, BASE + timedelta(days=2), excluding_reservation_id=reservation.reservation_id
    ) is True


def test_available_room_search_can_filter_by_type():
    pms = HotelAssistant()
    pms.add_room(make_room(1501, room_type="standard"))
    pms.add_room(make_room(1502, room_type="presidential"))

    rooms = get_available_rooms(pms, BASE, BASE + timedelta(days=1), room_type="presidential")

    assert [room.room_number for room in rooms] == [1502]


def test_invalid_date_range_is_rejected():
    pms = HotelAssistant()
    pms.add_room(make_room())

    with pytest.raises(ValueError, match="Check-out date must be after check-in date"):
        is_room_available(pms, 1501, BASE + timedelta(days=2), BASE)
