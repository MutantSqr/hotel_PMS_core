import pytest
from datetime import date

from app.assist import HotelAssistant
from app.models import Reservation, Room


def room(number=101, status="available", out_of_order=False, reason=None):
    return Room(number, 1, 2, [], "standard", status, out_of_order, reason, False)


def test_available_room_can_be_put_out_of_order_with_reason():
    pms = HotelAssistant()
    r = room()
    pms.add_room(r)
    pms.mark_room_out_of_order(101, "Broken HVAC")
    assert r.occupancy_status == "out_of_order"
    assert r.out_of_order is True
    assert r.out_of_order_reason == "Broken HVAC"


def test_maintenance_status_requires_reason():
    pms = HotelAssistant()
    pms.add_room(room())
    with pytest.raises(ValueError, match="reason is required"):
        pms.mark_room_out_of_service(101, "")


def test_occupied_room_cannot_be_taken_out_of_order():
    pms = HotelAssistant()
    r = room(status="occupied")
    r.current_guests = ["Alice"]
    pms.add_room(r)
    with pytest.raises(ValueError, match="occupied"):
        pms.mark_room_out_of_order(101, "Broken HVAC")


def test_reserved_room_with_active_reservation_cannot_be_taken_out_of_service():
    pms = HotelAssistant()
    r = room(status="reserved")
    pms.add_room(r)
    reservation = Reservation("RES101", ["Alice"], date(2026, 8, 20), date(2026, 8, 22), r, 100.0, "")
    pms.reservations[reservation.reservation_id] = reservation
    with pytest.raises(ValueError, match="active reservation"):
        pms.mark_room_out_of_service(101, "Renovation")


def test_out_of_order_room_can_be_restored_when_unreserved():
    pms = HotelAssistant()
    r = room()
    pms.add_room(r)
    pms.mark_room_out_of_order(101, "Broken lock")
    pms.restore_room(101)
    assert r.occupancy_status == "available"
    assert r.out_of_order is False
    assert r.out_of_order_reason is None


def test_invalid_room_status_is_rejected():
    pms = HotelAssistant()
    pms.add_room(room())
    with pytest.raises(ValueError, match="Invalid room status"):
        pms.set_room_status(101, "dirty")
