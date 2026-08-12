"""Reservation room-move rules.

The validator performs every check before mutating reservation or room state.
"""


def change_room(self, reservation_id, destination_room_number):
    if reservation_id not in self.reservations:
        raise ValueError(f"Error: Reservation {reservation_id} not found")

    reservation = self.reservations[reservation_id]
    if reservation.checked_out:
        raise ValueError(f"Error: Reservation {reservation_id} has already been checked out")
    if reservation.status == "checked_in" or reservation.checked_in:
        raise ValueError(f"Error: Reservation {reservation_id} is checked in and cannot be moved")
    if reservation.status in {"cancelled", "no_show"}:
        raise ValueError(f"Error: Reservation {reservation_id} is not active")

    destination = self.rooms.get(destination_room_number)
    if destination is None:
        raise ValueError(f"Error: Room {destination_room_number} not found")
    if destination.out_of_order:
        raise ValueError(f"Error: Room {destination_room_number} is out of order")
    if len(reservation.guest_names) > destination.capacity:
        raise ValueError(
            f"Error: Room {destination_room_number} can accommodate only {destination.capacity} guests"
        )

    for existing in self.reservations.values():
        if existing.reservation_id == reservation_id:
            continue
        if existing.room.room_number != destination_room_number:
            continue
        if existing.status in {"cancelled", "no_show", "checked_out"}:
            continue
        if self._reservation_dates_overlap(existing, reservation):
            raise ValueError(
                f"Error: Room {destination_room_number} is already reserved "
                f"from {existing.check_in_date} to {existing.check_out_date} "
                f"by reservation {existing.reservation_id}"
            )

    old_room = reservation.room
    if old_room.room_number == destination_room_number:
        return {
            "status": "success",
            "message": f"Reservation {reservation_id} is already assigned to room {destination_room_number}",
            "reservation_id": reservation_id,
            "old_room": old_room.room_number,
            "new_room": destination_room_number,
        }

    # All validation has completed. Mutation starts only here.
    reservation.room = destination
    if old_room.occupancy_status == "reserved":
        old_room.occupancy_status = "available"
    if destination.occupancy_status != "occupied":
        destination.occupancy_status = "reserved"

    for billing in self.billing_records.values():
        if billing.reservation.reservation_id == reservation_id:
            billing.room = destination

    return {
        "status": "success",
        "message": f"Reservation {reservation_id} moved from room {old_room.room_number} to room {destination_room_number}",
        "reservation_id": reservation_id,
        "old_room": old_room.room_number,
        "new_room": destination_room_number,
    }
