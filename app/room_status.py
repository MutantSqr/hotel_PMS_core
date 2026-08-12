"""Controlled room-status transitions for HotelAssistant."""

_ALLOWED = {"available", "reserved", "occupied", "out_of_order", "out_of_service"}
_BLOCKING = {"out_of_order", "out_of_service"}


def _has_active_reservation(pms, room_number):
    return any(
        reservation.room.room_number == room_number
        and getattr(reservation, "status", "confirmed") in {"confirmed", "checked_in"}
        for reservation in pms.reservations.values()
    )


def set_room_status(pms, room_number, status, reason=None):
    """Apply a validated maintenance/status transition without corrupting occupancy."""
    if status not in _ALLOWED:
        raise ValueError(f"Error: Invalid room status '{status}'")
    room = pms.rooms.get(room_number)
    if room is None:
        raise ValueError(f"Error: Room {room_number} not found")

    current = room.occupancy_status
    if status in _BLOCKING:
        if current == "occupied" or room.current_guests:
            raise ValueError(f"Error: Room {room_number} is occupied and cannot be placed {status}")
        if not reason or not reason.strip():
            raise ValueError(f"Error: A reason is required when placing room {room_number} {status}")
        if _has_active_reservation(pms, room_number):
            raise ValueError(f"Error: Room {room_number} has an active reservation")
        room.out_of_order = status == "out_of_order"
        room.out_of_order_reason = reason.strip()
        room.occupancy_status = status
        return status

    if current in _BLOCKING:
        if _has_active_reservation(pms, room_number):
            raise ValueError(f"Error: Room {room_number} has an active reservation and cannot become available")
        room.out_of_order = False
        room.out_of_order_reason = None

    if status == "reserved":
        if not _has_active_reservation(pms, room_number):
            raise ValueError(f"Error: Room {room_number} has no active reservation")
    if status == "occupied":
        if not room.current_guests:
            raise ValueError(f"Error: Room {room_number} has no checked-in guests")

    room.occupancy_status = status
    return status


def mark_room_out_of_order(pms, room_number, reason):
    return set_room_status(pms, room_number, "out_of_order", reason)


def mark_room_out_of_service(pms, room_number, reason):
    return set_room_status(pms, room_number, "out_of_service", reason)


def restore_room(pms, room_number):
    return set_room_status(pms, room_number, "available")
