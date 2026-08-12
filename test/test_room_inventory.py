import pytest

from app.assist import HotelAssistant
from app.models import Room
from app.room_inventory import inventory_by_type, room_is_sellable, set_showroom


def room(number, room_type="standard", showroom=False, out_of_order=False, status="available", capacity=2):
    floor = 15 if room_type == "presidential" else 1
    return Room(number, floor, capacity, [], room_type, status, out_of_order,
                "Maintenance" if out_of_order else None, showroom)


def test_showroom_is_not_sellable_but_remains_physical_inventory():
    pms = HotelAssistant()
    r = room(1501, showroom=True)
    pms.add_room(r)

    assert r.showroom is True
    assert room_is_sellable(r) is False
    assert inventory_by_type(pms)["standard"]["physical"] == 1
    assert inventory_by_type(pms)["standard"]["showrooms"] == 1
    assert inventory_by_type(pms)["standard"]["sellable"] == 0


def test_showroom_can_be_removed_without_changing_room_identity():
    pms = HotelAssistant()
    r = room(1501, showroom=True)
    pms.add_room(r)

    set_showroom(pms, 1501, False)

    assert r.showroom is False
    assert r.room_number == 1501
    assert room_is_sellable(r) is True


def test_occupied_room_cannot_become_showroom():
    pms = HotelAssistant()
    r = room(1501, status="occupied")
    r.current_guests = ["Alice"]
    pms.add_room(r)

    with pytest.raises(ValueError, match="occupied"):
        set_showroom(pms, 1501, True)


def test_presidential_inventory_is_exactly_one_when_one_room_exists():
    pms = HotelAssistant()
    pms.add_room(room(1501, room_type="presidential", capacity=4))

    inventory = inventory_by_type(pms)["presidential"]
    assert inventory["physical"] == 1
    assert inventory["sellable"] == 1


def test_presidential_showroom_removes_only_presidential_room_from_sellable_inventory():
    pms = HotelAssistant()
    pms.add_room(room(1501, room_type="presidential", showroom=True, capacity=4))

    inventory = inventory_by_type(pms)["presidential"]
    assert inventory["physical"] == 1
    assert inventory["showrooms"] == 1
    assert inventory["sellable"] == 0
