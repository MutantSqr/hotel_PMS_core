from datetime import date

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room


def make_pms():
    pms = HotelAssistant()
    room1 = Room(1501, 15, 2, [], "standard", "available", False, None, False)
    room2 = Room(1502, 15, 2, [], "standard", "available", False, None, False)
    pms.add_room(room1)
    pms.add_room(room2)
    pms.add_guest(Guest("Alice", "G001"))
    pms.add_guest(Guest("Bob", "G002"))
    return pms, room1, room2


def reservation(res_id, guest, check_in, check_out, room):
    return Reservation(res_id, [guest], check_in, check_out, room, 100.0, "")


def test_modification_allows_back_to_back_dates_for_same_room():
    pms, room, _ = make_pms()
    first = reservation("RES001", "Alice", date(2026, 8, 11), date(2026, 8, 13), room)
    second = reservation("RES002", "Bob", date(2026, 8, 13), date(2026, 8, 15), room)
    pms.add_reservation(first)
    pms.reservations[second.reservation_id] = second

    result = pms.modify_reservation("RES001", check_out_date=date(2026, 8, 13))

    assert result["status"] == "success"
    assert first.check_out_date == date(2026, 8, 13)


def test_modification_rejects_overlap_with_another_reservation():
    pms, room, _ = make_pms()
    first = reservation("RES001", "Alice", date(2026, 8, 11), date(2026, 8, 13), room)
    second = reservation("RES002", "Bob", date(2026, 8, 20), date(2026, 8, 22), room)
    pms.add_reservation(first)
    pms.reservations[second.reservation_id] = second

    with pytest.raises(ValueError, match="already reserved.*RES002"):
        pms.modify_reservation("RES001", check_in_date=date(2026, 8, 19), check_out_date=date(2026, 8, 21))


def test_modification_excludes_its_own_reservation_from_availability_check():
    pms, room, _ = make_pms()
    first = reservation("RES001", "Alice", date(2026, 8, 11), date(2026, 8, 13), room)
    pms.add_reservation(first)

    result = pms.modify_reservation(
        "RES001",
        check_in_date=date(2026, 8, 12),
        check_out_date=date(2026, 8, 14),
    )

    assert result["status"] == "success"
    assert first.check_in_date == date(2026, 8, 12)
    assert first.check_out_date == date(2026, 8, 14)
