"""Reservation modification integration with the centralized availability engine."""

from app.availability import is_room_available


def modify_reservation_with_availability(
    assistant,
    reservation_id,
    check_in_date=None,
    check_out_date=None,
    room=None,
    guest_names=None,
    expected_daily_rate=None,
    special_requests=None,
):
    """Validate the proposed room/date change through the central availability authority.

    The existing HotelAssistant modification method remains the compatibility layer for
    the rest of the PMS. This function adds the authoritative availability gate first.
    """
    if reservation_id not in assistant.reservations:
        raise ValueError(f"Error: Reservation {reservation_id} not found")

    reservation = assistant.reservations[reservation_id]
    new_check_in = check_in_date if check_in_date is not None else reservation.check_in_date
    new_check_out = check_out_date if check_out_date is not None else reservation.check_out_date
    new_room = room if room is not None else reservation.room

    room_number = new_room.room_number if new_room is not None else None
    if room_number is not None and room_number in assistant.rooms:
        available = is_room_available(
            assistant,
            room_number,
            new_check_in,
            new_check_out,
            excluding_reservation_id=reservation_id,
        )
        if not available:
            for existing in assistant.reservations.values():
                if existing.reservation_id == reservation_id:
                    continue
                if existing.room.room_number != room_number:
                    continue
                if getattr(existing, "status", "confirmed") in {"cancelled", "no_show", "checked_out"}:
                    continue
                if existing.check_in_date < new_check_out and existing.check_out_date > new_check_in:
                    raise ValueError(
                        f"Error: Room {room_number} is already reserved "
                        f"from {existing.check_in_date} to {existing.check_out_date} "
                        f"by reservation {existing.reservation_id}"
                    )
            raise ValueError(f"Error: Room {room_number} is not available for the requested dates")

    return assistant._modify_reservation_legacy(
        reservation_id,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        room=room,
        guest_names=guest_names,
        expected_daily_rate=expected_daily_rate,
        special_requests=special_requests,
    )
