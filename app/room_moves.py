"""Room-move domain rules.

This module is intentionally small: it validates a proposed room move without
mutating the PMS. The service layer should call ``validate_room_move`` before
changing the reservation's room assignment.
"""


def validate_room_move(pms, reservation, destination_room_number):
    if reservation.status in {"checked_in", "checked_out", "no_show", "cancelled"}:
        if reservation.status == "checked_in":
            raise ValueError("Cannot move a checked in reservation")
        raise ValueError("Cannot move an inactive reservation")

    destination = pms.rooms.get(destination_room_number)
    if destination is None:
        raise ValueError(f"Room {destination_room_number} does not exist")

    if getattr(destination, "status", None) == "out_of_order":
        raise ValueError(f"Room {destination_room_number} is out of order")

    guest_count = len(getattr(reservation, "guests", []))
    capacity = getattr(destination, "capacity", 0)
    if guest_count > capacity:
        raise ValueError(f"Room {destination_room_number} capacity is insufficient")

    for other in pms.reservations.values():
        if other.reservation_id == reservation.reservation_id:
            continue
        if other.room_number != destination_room_number:
            continue
        if getattr(other, "status", None) in {"cancelled", "no_show", "checked_out"}:
            continue
        if reservation.check_in < other.check_out and other.check_in < reservation.check_out:
            raise ValueError(f"Room {destination_room_number} is already reserved")

    return destination
