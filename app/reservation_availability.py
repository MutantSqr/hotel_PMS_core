"""Reservation creation integration with the centralized availability engine."""

from app.availability import is_room_available


def add_reservation_with_availability(self, reservation):
    """Create a reservation only when its room/date interval is available."""
    if reservation.reservation_id in self.reservations:
        raise ValueError(f"Error: Reservation {reservation.reservation_id} already exists")

    room_number = reservation.room.room_number
    if room_number not in self.rooms:
        raise ValueError(f"Error: Room {room_number} not found")

    if not is_room_available(
        self,
        room_number,
        reservation.check_in_date,
        reservation.check_out_date,
    ):
        raise ValueError(f"Error: Room {room_number} is not available for the requested dates")

    room = self.rooms[room_number]
    if len(reservation.guest_names) > room.capacity:
        raise ValueError(
            f"Error: Room {room_number} can accommodate only {room.capacity} guests"
        )

    guest_map = {}
    for name in reservation.guest_names:
        matches = [g for g in self.guests.values() if g.name == name]
        if len(matches) == 0:
            raise ValueError(f"Error: Guest '{name}' is not registered in the system")
        if len(matches) > 1:
            raise ValueError(
                f"Error: Guest name '{name}' is ambiguous ({len(matches)} matches). "
                f"Register guests with unique names or resolve by confirmation number."
            )
        guest_map[name] = matches[0].confirmation_number

    self.reservations[reservation.reservation_id] = reservation
    self._reservation_guest_map[reservation.reservation_id] = guest_map
    if room.occupancy_status != "occupied":
        room.occupancy_status = "reserved"
