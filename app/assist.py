from datetime import datetime
from app.models import Billing


class HotelAssistant:
    def __init__(self):
        self.reservations = {}
        self.rooms = {}
        self.guests = {}
        self.vehicles = {}
        self.billing_records = {}
        self.billing_counter = 0
        # FIX: per-reservation name -> confirmation_number map, built once at
        # add_reservation time. This replaces the old global "search every
        # guest in the hotel by name" lookup used inside check_in/check_out,
        # which could silently grab the wrong guest if two people shared a
        # name anywhere in the system.
        self._reservation_guest_map = {}

    # -----------------------------------------------------------------
    # Registry methods
    # FIX: all three now reject duplicate keys instead of silently
    # overwriting existing rooms / reservations / guests.
    # -----------------------------------------------------------------

    def add_room(self, room):
        if room.room_number in self.rooms:
            raise ValueError(f"Error: Room {room.room_number} already exists")
        self.rooms[room.room_number] = room

    def _reservation_dates_overlap(self, first, second):
        """Return True when two reservations occupy the room at the same time."""
        return (
            first.check_in_date < second.check_out_date
            and first.check_out_date > second.check_in_date
        )

    def add_reservation(self, reservation):
        if reservation.reservation_id in self.reservations:
            raise ValueError(f"Error: Reservation {reservation.reservation_id} already exists")

        if reservation.room.room_number not in self.rooms:
            raise ValueError(f"Error: Room {reservation.room.room_number} not found")

        if reservation.room.out_of_order:
            raise ValueError(
                f"Error: Room {reservation.room.room_number} is out of order and cannot be reserved"
            )

        # FIX: a room may be reserved again after the previous guest checks
        # out, but two active reservations may never overlap. Check the date
        # ranges instead of using the room's current occupancy_status because
        # that status represents the room right now, not its future inventory.
        for existing in self.reservations.values():
            if existing.room.room_number != reservation.room.room_number:
                continue

            # Completed stays no longer consume future inventory. Cancelled
            # and no-show states will be added to this lifecycle as those
            # workflows are implemented.
            if getattr(existing, "status", "confirmed") in {"cancelled", "no_show"}:
                continue

            if self._reservation_dates_overlap(existing, reservation):
                raise ValueError(
                    f"Error: Room {reservation.room.room_number} is already reserved "
                    f"from {existing.check_in_date} to {existing.check_out_date} "
                    f"by reservation {existing.reservation_id}"
                )

        # FIX: resolve every guest_name on this reservation to an actual
        # registered Guest right now, at reservation-creation time, instead
        # of waiting until check-in and hoping a name-based search finds the
        # right person. Ambiguous or missing guests fail loudly, here,
        # before the reservation is accepted.
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

        # A reservation exists independently of the room's current physical
        # occupancy. Marking the room reserved here is still useful for a
        # simple current-state display, but date overlap is what controls
        # future inventory.
        reservation.room.occupancy_status = "reserved"

    def add_guest(self, guest):
        if guest.confirmation_number in self.guests:
            raise ValueError(f"Error: Guest with confirmation {guest.confirmation_number} already exists")
        self.guests[guest.confirmation_number] = guest

    # -----------------------------------------------------------------
    # Check-in / Check-out
    # -----------------------------------------------------------------

    def check_in_guest(self, reservation_id, guest_name, vehicle=None):
        if reservation_id not in self.reservations:
            raise ValueError(f"Error: Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]

        if guest_name not in reservation.guest_names:
            raise ValueError(f"Error: Guest '{guest_name}' is not part of reservation {reservation_id}")

        if getattr(reservation, "status", "confirmed") in {"cancelled", "no_show", "checked_out"}:
            raise ValueError(f"Error: Reservation {reservation_id} is not eligible for check-in")

        # FIX: added guard. Previously nothing stopped the same reservation
        # from being checked in twice.
        if reservation.checked_in:
            raise ValueError(f"Error: Reservation {reservation_id} has already been checked in")

        room_number = reservation.room.room_number
        if room_number not in self.rooms:
            raise ValueError(f"Error: Room {room_number} not found")

        room = self.rooms[room_number]

        # FIX: the old check required the room's global status to be
        # "reserved". That breaks legitimate back-to-back stays because the
        # prior guest checks out and makes the room "available" even though a
        # future reservation exists. The reservation itself is the authority
        # for this check-in; only an actually occupied room blocks it.
        if room.occupancy_status == "occupied":
            raise ValueError(f"Error: Room {room_number} is currently occupied")

        if room.out_of_order:
            raise ValueError(f"Error: Room {room_number} is out of order")

        confirmation_number = self._reservation_guest_map[reservation_id][guest_name]
        guest = self.guests[confirmation_number]

        total_bill = reservation.calculate_total_expected_bill()
        billing_id = f"BILL{self.billing_counter + 1:04d}"

        billing = Billing(
            billing_id=billing_id,
            guest=guest,
            room=room,
            reservation=reservation,
            amount_due=total_bill,
            amount_paid=0,
            billing_date=datetime.now(),
            payment_method="Pending"
        )

        room.occupancy_status = "occupied"
        room.current_guest = guest_name

        if vehicle:
            room.vehicle = vehicle
            self.vehicles[vehicle.vehicle_id] = vehicle

        reservation.checked_in = True
        self.billing_counter += 1
        self.billing_records[billing_id] = billing

        return {
            "status": "success",
            "message": f"Guest {guest_name} checked in to room {room_number}",
            "room_number": room_number,
            "billing_id": billing_id,
            "amount_due": total_bill,
            "vehicle": vehicle.vehicle_id if vehicle else "None"
        }

    def check_out_guest(self, reservation_id, guest_name, amount_paid=0):
        if reservation_id not in self.reservations:
            raise ValueError(f"Error: Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]

        if guest_name not in reservation.guest_names:
            raise ValueError(f"Error: Guest '{guest_name}' is not part of reservation {reservation_id}")

        if not reservation.checked_in:
            raise ValueError(f"Error: Guest '{guest_name}' has not checked in yet")

        if reservation.checked_out:
            raise ValueError(f"Error: Guest '{guest_name}' has already been checked out")

        if amount_paid < 0:
            raise ValueError("Error: Amount paid cannot be negative")

        room_number = reservation.room.room_number
        if room_number not in self.rooms:
            raise ValueError(f"Error: Room {room_number} not found")

        room = self.rooms[room_number]

        if room.current_guest != guest_name:
            raise ValueError(f"Error: Guest '{guest_name}' is not currently in room {room_number}")

        confirmation_number = self._reservation_guest_map[reservation_id][guest_name]
        billing_record = next(
            (b for b in self.billing_records.values()
             if b.reservation.reservation_id == reservation_id
             and b.guest.confirmation_number == confirmation_number),
            None
        )

        if billing_record is None:
            raise ValueError(f"Error: No billing record found for reservation {reservation_id}")

        vehicle_removed = None
        if room.vehicle:
            vehicle_removed = room.vehicle.vehicle_id

        billing_record.amount_paid = amount_paid

        if amount_paid > 0:
            billing_record.payment_method = "Paid"

        if vehicle_removed:
            del self.vehicles[vehicle_removed]
            room.vehicle = None

        room.occupancy_status = "available"
        room.current_guest = None
        reservation.checked_out = True
        reservation.status = "checked_out"

        return {
            "status": "success",
            "message": f"Guest {guest_name} checked out from room {room_number}",
            "room_number": room_number,
            "billing_id": billing_record.billing_id,
            "amount_due": billing_record.amount_due,
            "amount_paid": amount_paid,
            "balance": billing_record.balance,
            "vehicle_removed": vehicle_removed if vehicle_removed else "None"
        }
