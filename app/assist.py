from datetime import datetime, timedelta
from app.models import Billing


class HotelAssistant:
    def __init__(self):
        self.reservations = {}
        self.rooms = {}
        self.guests = {}
        self.vehicles = {}
        self.billing_records = {}
        self.billing_counter = 0
        self._reservation_guest_map = {}

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

        for existing in self.reservations.values():
            if existing.room.room_number != reservation.room.room_number:
                continue
            if getattr(existing, "status", "confirmed") in {"cancelled", "no_show"}:
                continue
            if self._reservation_dates_overlap(existing, reservation):
                raise ValueError(
                    f"Error: Room {reservation.room.room_number} is already reserved "
                    f"from {existing.check_in_date} to {existing.check_out_date} "
                    f"by reservation {existing.reservation_id}"
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
        reservation.room.occupancy_status = "reserved"

    def add_guest(self, guest):
        if guest.confirmation_number in self.guests:
            raise ValueError(f"Error: Guest with confirmation {guest.confirmation_number} already exists")
        self.guests[guest.confirmation_number] = guest

    def _get_reservation_guest(self, reservation_id, guest_name):
        confirmation_number = self._reservation_guest_map[reservation_id][guest_name]
        return self.guests[confirmation_number]

    def _create_billing(self, guest, room, reservation, amount_due, tax_amount=0,
                        payment_method="Pending"):
        billing_id = f"BILL{self.billing_counter + 1:04d}"
        billing = Billing(
            billing_id=billing_id,
            guest=guest,
            room=room,
            reservation=reservation,
            amount_due=amount_due,
            amount_paid=0,
            tax_amount=tax_amount,
            billing_date=datetime.now(),
            payment_method=payment_method
        )
        self.billing_counter += 1
        self.billing_records[billing_id] = billing
        return billing

    def check_in_guest(self, reservation_id, guest_name, vehicle=None):
        if reservation_id not in self.reservations:
            raise ValueError(f"Error: Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]

        if guest_name not in reservation.guest_names:
            raise ValueError(f"Error: Guest '{guest_name}' is not part of reservation {reservation_id}")

        if reservation.status in {"cancelled", "no_show", "checked_out"}:
            raise ValueError(f"Error: Reservation {reservation_id} is not eligible for check-in")

        if reservation.checked_in:
            raise ValueError(f"Error: Reservation {reservation_id} has already been checked in")

        room_number = reservation.room.room_number
        if room_number not in self.rooms:
            raise ValueError(f"Error: Room {room_number} not found")

        room = self.rooms[room_number]

        if room.occupancy_status == "occupied":
            raise ValueError(f"Error: Room {room_number} is currently occupied")

        if room.out_of_order:
            raise ValueError(f"Error: Room {room_number} is out of order")

        guest = self._get_reservation_guest(reservation_id, guest_name)
        total_bill = reservation.calculate_total_expected_bill()
        billing = self._create_billing(guest, room, reservation, total_bill)

        room.occupancy_status = "occupied"
        room.current_guest = guest_name

        if vehicle:
            room.vehicle = vehicle
            self.vehicles[vehicle.vehicle_id] = vehicle

        reservation.checked_in = True
        reservation.status = "checked_in"

        return {
            "status": "success",
            "message": f"Guest {guest_name} checked in to room {room_number}",
            "room_number": room_number,
            "billing_id": billing.billing_id,
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

    def run_night_audit(self, audit_datetime, tax_rate):
        """Process no-shows at the 2:30 AM Night Audit cutoff.

        The audit at 2:30 AM processes the prior business day's arrivals.
        A no-show is charged one room night plus tax, then its room is
        released for future inventory.
        """
        if audit_datetime.hour < 2 or (audit_datetime.hour == 2 and audit_datetime.minute < 30):
            raise ValueError("Error: Night Audit no-show processing cannot run before 2:30 AM")
        if not 0 <= tax_rate <= 1:
            raise ValueError("Error: Tax rate must be between 0 and 1")

        arrival_date = (audit_datetime - timedelta(days=1)).date()
        processed = []

        for reservation in self.reservations.values():
            if reservation.check_in_date.date() != arrival_date:
                continue
            if reservation.status != "confirmed" or reservation.checked_in:
                continue

            guest_name = reservation.guest_names[0]
            guest = self._get_reservation_guest(reservation.reservation_id, guest_name)
            room = reservation.room

            room_charge = reservation.expected_daily_rate
            tax_amount = round(room_charge * tax_rate, 2)
            total_due = round(room_charge + tax_amount, 2)

            billing = self._create_billing(
                guest=guest,
                room=room,
                reservation=reservation,
                amount_due=total_due,
                tax_amount=tax_amount,
                payment_method="No-Show Charge"
            )

            reservation.status = "no_show"
            room.occupancy_status = "available"
            room.current_guest = None
            room.vehicle = None

            processed.append({
                "reservation_id": reservation.reservation_id,
                "room_number": room.room_number,
                "status": reservation.status,
                "room_charge": room_charge,
                "tax_amount": tax_amount,
                "amount_due": total_due,
                "billing_id": billing.billing_id
            })

        return processed
