"""Single source of truth for room availability decisions."""

from datetime import datetime


_BLOCKED_RESERVATION_STATUSES = {"cancelled", "no_show", "checked_out"}


def _validate_dates(check_in_date, check_out_date):
    if check_in_date >= check_out_date:
        raise ValueError("Error: Check-out date must be after check-in date")


def _dates_overlap(first_check_in, first_check_out, second_check_in, second_check_out):
    return first_check_in < second_check_out and first_check_out > second_check_in


def is_room_available(pms, room_number, check_in_date, check_out_date, excluding_reservation_id=None):
    """Return whether a physical room can be assigned for the complete stay."""
    _validate_dates(check_in_date, check_out_date)

    room = pms.rooms.get(room_number)
    if room is None:
        raise ValueError(f"Error: Room {room_number} not found")

    if room.showroom:
        return False
    if room.out_of_order:
        return False
    if room.occupancy_status == "out_of_service":
        return False

    for reservation in pms.reservations.values():
        if reservation.reservation_id == excluding_reservation_id:
            continue
        if reservation.room.room_number != room_number:
            continue
        if getattr(reservation, "status", "confirmed") in _BLOCKED_RESERVATION_STATUSES:
            continue
        if _dates_overlap(
            reservation.check_in_date,
            reservation.check_out_date,
            check_in_date,
            check_out_date,
        ):
            return False

    # A currently occupied room is unavailable unless the requested interval
    # is being evaluated as part of its own excluded reservation.
    if room.occupancy_status == "occupied" and excluding_reservation_id is None:
        return False

    return True


def get_available_rooms(pms, check_in_date, check_out_date, room_type=None):
    """Return physical rooms that are sellable for the requested date range."""
    _validate_dates(check_in_date, check_out_date)
    rooms = []
    for room in pms.rooms.values():
        if room_type is not None and room.room_type != room_type:
            continue
        if is_room_available(pms, room.room_number, check_in_date, check_out_date):
            rooms.append(room)
    return rooms
