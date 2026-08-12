"""Room inventory and sellable-inventory rules."""


def room_is_sellable(room):
    """Return whether a physical room is currently sellable to guests."""
    return not room.showroom and not room.out_of_order and room.occupancy_status == "available"


def inventory_by_type(pms):
    """Return physical, showroom, out-of-order, and sellable counts by room type."""
    inventory = {}
    for room in pms.rooms.values():
        data = inventory.setdefault(room.room_type, {
            "physical": 0,
            "showrooms": 0,
            "out_of_order": 0,
            "out_of_service": 0,
            "sellable": 0,
        })
        data["physical"] += 1
        if room.showroom:
            data["showrooms"] += 1
        if room.out_of_order:
            data["out_of_order"] += 1
        if room.occupancy_status == "out_of_service":
            data["out_of_service"] += 1
        if room_is_sellable(room):
            data["sellable"] += 1
    return inventory


def set_showroom(pms, room_number, is_showroom=True):
    """Set showroom designation without changing the room's physical identity."""
    room = pms.rooms.get(room_number)
    if room is None:
        raise ValueError(f"Error: Room {room_number} not found")
    if is_showroom and (room.current_guests or room.occupancy_status == "occupied"):
        raise ValueError(f"Error: Room {room_number} is occupied and cannot become a showroom")
    if is_showroom and room.out_of_order:
        raise ValueError(f"Error: Room {room_number} is out of order")
    room.showroom = bool(is_showroom)
    return room.showroom
