from datetime import datetime

import pytest

from app.assist import HotelAssistant
from app.models import Guest, Reservation, Room


def make_guest(name, confirmation):
    return Guest(
        name=name,
        contact_details=f"{name.lower()}@example.com",
        billing_information="card",
        group_affiliation="",
        special_comments="",
        confirmation_number=confirmation,
    )


def make_room(number):
    return Room(
        room_number=number,
        floor_number=number // 100,
        capacity=2,
        amenities=[],
        room_type="standard",
        occupancy_status="available",
        out_of_order=False,
        out_of_order_reason="",
        showroom=False,
    )


def make_reservation(reservation_id, guest_name, room, check_in, check_out):
    return Reservation(
        reservation_id=reservation_id,
        guest_names=[guest_name],
        check_in_date=check_in,
        check_out_date=check_out,
        room=room,
        expected_daily_rate=100,
        special_requests="",
    )


def setup_pms():
    pms = HotelAssistant()
    room_1501 = make_room(1501)
    room_1502 = make_room(1502)
    pms.add_room(room_1501)
    pms.add_room(room_1502)
    pms.add_guest(make_guest("Alice", "G001"))
    pms.add_guest(make_guest("Bob", "G002"))
    return pms, room_1501, room_1502


def test_reservation_modification_reuses_overlap_rules():
    pms, room_1501, _ = setup_pms()
    res1 = make_reservation(
        "RES001", "Alice", room_1501,
        datetime(2026, 8, 11), datetime(2026, 8, 13),
    )
    res2 = make_reservation(
        "RES002", "Bob", room_1501,
        datetime(2026, 8, 20), datetime(2026, 8, 22),
    )
    pms.add_reservation(res1)
    pms.add_reservation(res2)

    with pytest.raises(ValueError, match="already reserved"):
        pms.modify_reservation(
            "RES002",
            check_in_date=datetime(2026, 8, 12),
            check_out_date=datetime(2026, 8, 15),
        )

    assert res2.check_in_date == datetime(2026, 8, 20)
    assert res2.check_out_date == datetime(2026, 8, 22)


def test_reservation_modification_allows_back_to_back_dates():
    pms, room_1501, _ = setup_pms()
    res1 = make_reservation(
        "RES001", "Alice", room_1501,
        datetime(2026, 8, 11), datetime(2026, 8, 13),
    )
    res2 = make_reservation(
        "RES002", "Bob", room_1501,
        datetime(2026, 8, 20), datetime(2026, 8, 22),
    )
    pms.add_reservation(res1)
    pms.add_reservation(res2)

    result = pms.modify_reservation(
        "RES002",
        check_in_date=datetime(2026, 8, 13),
        check_out_date=datetime(2026, 8, 15),
    )

    assert result["status"] == "success"
    assert res2.check_in_date == datetime(2026, 8, 13)
    assert res2.check_out_date == datetime(2026, 8, 15)


def test_checked_in_reservation_cannot_have_dates_modified():
    pms, room_1501, _ = setup_pms()
    res = make_reservation(
        "RES001", "Alice", room_1501,
        datetime(2026, 8, 11), datetime(2026, 8, 13),
    )
    pms.add_reservation(res)
    pms.check_in_guest("RES001", "Alice", current_datetime=datetime(2026, 8, 11, 15))

    with pytest.raises(ValueError, match="cannot be modified"):
        pms.modify_reservation(
            "RES001",
            check_in_date=datetime(2026, 8, 12),
            check_out_date=datetime(2026, 8, 14),
        )


def test_reservation_modification_validates_dates_before_changing_state():
    pms, room_1501, _ = setup_pms()
    res = make_reservation(
        "RES001", "Alice", room_1501,
        datetime(2026, 8, 20), datetime(2026, 8, 22),
    )
    pms.add_reservation(res)

    with pytest.raises(ValueError, match="Check-out date must be after check-in date"):
        pms.modify_reservation(
            "RES001",
            check_in_date=datetime(2026, 8, 22),
            check_out_date=datetime(2026, 8, 22),
        )

    assert res.check_in_date == datetime(2026, 8, 20)
    assert res.check_out_date == datetime(2026, 8, 22)
