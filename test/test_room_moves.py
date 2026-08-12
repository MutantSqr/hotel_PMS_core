import pytest
from datetime import date

from app.assist import HotelPMSAssistant
from app.core import HotelPMS


def make_pms():
    return HotelPMSAssistant(HotelPMS())


def test_future_reservation_can_change_to_available_room():
    pms = make_pms()
    pms.add_room("1501", "Presidential Suite", 4, 500.0)
    pms.add_room("1502", "King", 2, 200.0)
    res = pms.reserve_room("RES001", "1501", date(2026, 8, 20), date(2026, 8, 22), ["Alice"])

    pms.change_room("RES001", "1502")

    assert res.room_number == "1502"
    assert pms.reservations["RES001"].room_number == "1502"


def test_room_move_rejects_overlapping_destination_without_releasing_old_room():
    pms = make_pms()
    pms.add_room("1501", "King", 2, 200.0)
    pms.add_room("1502", "King", 2, 200.0)
    pms.reserve_room("RES001", "1501", date(2026, 8, 20), date(2026, 8, 22), ["Alice"])
    pms.reserve_room("RES002", "1502", date(2026, 8, 21), date(2026, 8, 23), ["Bob"])

    with pytest.raises(ValueError, match="already reserved"):
        pms.change_room("RES001", "1502")

    assert pms.reservations["RES001"].room_number == "1501"


def test_room_move_rejects_out_of_order_destination():
    pms = make_pms()
    pms.add_room("1501", "King", 2, 200.0)
    pms.add_room("1502", "King", 2, 200.0)
    pms.rooms["1502"].status = "out_of_order"
    pms.reserve_room("RES001", "1501", date(2026, 8, 20), date(2026, 8, 22), ["Alice"])

    with pytest.raises(ValueError, match="out of order"):
        pms.change_room("RES001", "1502")

    assert pms.reservations["RES001"].room_number == "1501"


def test_room_move_rejects_wrong_capacity():
    pms = make_pms()
    pms.add_room("1501", "King", 2, 200.0)
    pms.add_room("1502", "Single", 1, 100.0)
    pms.reserve_room("RES001", "1501", date(2026, 8, 20), date(2026, 8, 22), ["Alice", "Bob"])

    with pytest.raises(ValueError, match="capacity"):
        pms.change_room("RES001", "1502")

    assert pms.reservations["RES001"].room_number == "1501"


def test_checked_in_reservation_cannot_be_moved_without_explicit_room_move_support():
    pms = make_pms()
    pms.add_room("1501", "King", 2, 200.0)
    pms.add_room("1502", "King", 2, 200.0)
    pms.reserve_room("RES001", "1501", date(2026, 8, 20), date(2026, 8, 22), ["Alice"])
    pms.check_in("RES001", "Alice")

    with pytest.raises(ValueError, match="checked in"):
        pms.change_room("RES001", "1502")

    assert pms.reservations["RES001"].room_number == "1501"
