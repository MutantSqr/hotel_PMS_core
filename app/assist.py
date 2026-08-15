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
        self.pm_accounts = {}
        self._reservation_guest_map = {}

    def add_room(self, room):
        if room.room_number in self.rooms:
            raise ValueError(f"Error: Room {room.room_number} already exists")
        self.rooms[room.room_number] = room

    def _reservation_dates_overlap(self, first, second):
        return (
            first.check_in_date < second.check_out_date
            and first.check_out_date > second.check_in_date
        )

    def _room_has_future_reservation(self, room_number, excluding_reservation_id=None):
        now = datetime.now()
        return any(
            other.reservation_id != excluding_reservation_id
            and other.room.room_number == room_number
            and getattr(other, "status", "confirmed") == "confirmed"
            and other.check_out_date > now
            for other in self.reservations.values()
        )

    def add_reservation(self, reservation):
        if reservation.reservation_id in self.reservations:
            raise ValueError(f"Error: Reservation {reservation.reservation_id} already exists")

        room_number = reservation.room.room_number
        if room_number not in self.rooms:
            raise ValueError(f"Error: Room {room_number} not found")
        room = self.rooms[room_number]

        if room.out_of_order:
            raise ValueError(f"Error: Room {room_number} is out of order and cannot be reserved")

        for existing in self.reservations.values():
            if existing.room.room_number != room_number:
                continue
            if getattr(existing, "status", "confirmed") in {"cancelled", "no_show", "checked_out"}:
                continue
            if self._reservation_dates_overlap(existing, reservation):
                raise ValueError(
                    f"Error: Room {room_number} is already reserved "
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
        if room.occupancy_status != "occupied":
            room.occupancy_status = "reserved"

    def modify_reservation(self, reservation_id, check_in_date=None, check_out_date=None,
                           room=None, guest_names=None, expected_daily_rate=None,
                           special_requests=None):
        """Safely modify a confirmed reservation using the same room/date rules as creation."""
        if reservation_id not in self.reservations:
            raise ValueError(f"Error: Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]
        if reservation.status != "confirmed" or reservation.checked_in or reservation.checked_out:
            raise ValueError(
                f"Error: Reservation {reservation_id} cannot be modified from status '{reservation.status}'"
            )

        new_check_in = check_in_date if check_in_date is not None else reservation.check_in_date
        new_check_out = check_out_date if check_out_date is not None else reservation.check_out_date
        new_room = room if room is not None else reservation.room
        new_guest_names = list(guest_names) if guest_names is not None else list(reservation.guest_names)
        new_rate = expected_daily_rate if expected_daily_rate is not None else reservation.expected_daily_rate
        new_requests = special_requests if special_requests is not None else reservation.special_requests

        if new_check_in >= new_check_out:
            raise ValueError("Error: Check-out date must be after check-in date")
        if not new_guest_names:
            raise ValueError("Error: At least one guest name is required")
        if len(set(new_guest_names)) != len(new_guest_names):
            raise ValueError("Error: A guest cannot be listed more than once on the same reservation")
        if new_rate <= 0:
            raise ValueError("Error: Expected daily rate must be positive")
        if new_room is None:
            raise ValueError("Error: Reservation must be linked to a room")

        room_number = new_room.room_number
        if room_number not in self.rooms:
            raise ValueError(f"Error: Room {room_number} not found")
        registered_room = self.rooms[room_number]
        if registered_room.out_of_order:
            raise ValueError(f"Error: Room {room_number} is out of order and cannot be reserved")
        if len(new_guest_names) > registered_room.capacity:
            raise ValueError(f"Error: Room {room_number} can accommodate only {registered_room.capacity} guests")

        guest_map = {}
        for name in new_guest_names:
            matches = [g for g in self.guests.values() if g.name == name]
            if len(matches) == 0:
                raise ValueError(f"Error: Guest '{name}' is not registered in the system")
            if len(matches) > 1:
                raise ValueError(
                    f"Error: Guest name '{name}' is ambiguous ({len(matches)} matches). "
                    f"Register guests with unique names or resolve by confirmation number."
                )
            guest_map[name] = matches[0].confirmation_number

        candidate = type(reservation)(
            reservation_id=reservation.reservation_id,
            guest_names=new_guest_names,
            check_in_date=new_check_in,
            check_out_date=new_check_out,
            room=registered_room,
            expected_daily_rate=new_rate,
            special_requests=new_requests,
        )

        for existing in self.reservations.values():
            if existing.reservation_id == reservation_id:
                continue
            if existing.room.room_number != room_number:
                continue
            if getattr(existing, "status", "confirmed") in {"cancelled", "no_show", "checked_out"}:
                continue
            if self._reservation_dates_overlap(existing, candidate):
                raise ValueError(
                    f"Error: Room {room_number} is already reserved "
                    f"from {existing.check_in_date} to {existing.check_out_date} "
                    f"by reservation {existing.reservation_id}"
                )

        old_room = reservation.room
        reservation.check_in_date = new_check_in
        reservation.check_out_date = new_check_out
        reservation.room = registered_room
        reservation.guest_names = new_guest_names
        reservation.expected_daily_rate = new_rate
        reservation.special_requests = new_requests
        self._reservation_guest_map[reservation_id] = guest_map

        if old_room.room_number != registered_room.room_number:
            if old_room.occupancy_status == "reserved":
                old_room.occupancy_status = "available"
            if registered_room.occupancy_status != "occupied":
                registered_room.occupancy_status = "reserved"

        return {
            "status": "success",
            "message": f"Reservation {reservation_id} modified",
            "reservation_id": reservation_id,
            "room_number": registered_room.room_number,
            "check_in_date": reservation.check_in_date,
            "check_out_date": reservation.check_out_date,
            "guest_names": list(reservation.guest_names),
            "expected_daily_rate": reservation.expected_daily_rate,
        }

    def cancel_reservation(self, reservation_id):
        if reservation_id not in self.reservations:
            raise ValueError(f"Error: Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]
        if reservation.status != "confirmed" or reservation.checked_in or reservation.checked_out:
            raise ValueError(
                f"Error: Reservation {reservation_id} cannot be cancelled from status '{reservation.status}'"
            )

        reservation.status = "cancelled"
        room = self.rooms[reservation.room.room_number]
        has_future_reservation = self._room_has_future_reservation(
            room.room_number, excluding_reservation_id=reservation_id
        )
        if not has_future_reservation and room.occupancy_status != "occupied":
            room.occupancy_status = "available"

        return {
            "status": "success",
            "message": f"Reservation {reservation_id} cancelled",
            "reservation_id": reservation_id,
            "room_number": room.room_number,
            "room_status": room.occupancy_status,
        }

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

    def _get_reservation_billing(self, reservation_id):
        return next(
            (b for b in self.billing_records.values() if b.reservation.reservation_id == reservation_id),
            None
        )

    def check_in_guest(self, reservation_id, guest_name, vehicle=None, accompanying_guest_names=None, current_datetime=None):
        if reservation_id not in self.reservations:
            raise ValueError(f"Error: Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]
        current_datetime = current_datetime or datetime.now()
        checked_in_names = list(getattr(reservation, "checked_in_guest_names", []))

        if guest_name not in reservation.guest_names:
            raise ValueError(f"Error: Guest '{guest_name}' is not part of reservation {reservation_id}")
        if reservation.status in {"cancelled", "no_show", "checked_out"}:
            raise ValueError(f"Error: Reservation {reservation_id} is not eligible for check-in")
        if guest_name in checked_in_names:
            raise ValueError(f"Error: Guest '{guest_name}' has already been checked in")
        if current_datetime < reservation.check_in_date:
            raise ValueError(
                f"Error: Reservation {reservation_id} is not due for check-in until {reservation.check_in_date}"
            )
        if current_datetime >= reservation.check_out_date:
            raise ValueError(f"Error: Reservation {reservation_id} has passed its check-out date")

        room_number = reservation.room.room_number
        if room_number not in self.rooms:
            raise ValueError(f"Error: Room {room_number} not found")
        room = self.rooms[room_number]
        if room.out_of_order:
            raise ValueError(f"Error: Room {room_number} is out of order")

        for other in self.reservations.values():
            if other.reservation_id == reservation_id:
                continue
            if other.room.room_number != room_number or other.status != "checked_in":
                continue
            if self._reservation_dates_overlap(other, reservation):
                raise ValueError(
                    f"Error: Room {room_number} is already occupied by reservation {other.reservation_id}"
                )

        accompanying_guest_names = accompanying_guest_names or []
        check_in_names = checked_in_names + [guest_name] + accompanying_guest_names
        if len(check_in_names) > room.capacity:
            raise ValueError(f"Error: Room {room_number} can accommodate only {room.capacity} guests")
        if len(set(check_in_names)) != len(check_in_names):
            raise ValueError("Error: A guest cannot be checked in more than once")
        for name in check_in_names:
            if name not in reservation.guest_names:
                raise ValueError(f"Error: Guest '{name}' is not part of reservation {reservation_id}")
            if name not in self._reservation_guest_map[reservation_id]:
                raise ValueError(f"Error: Guest '{name}' is not registered in the system")

        if not checked_in_names and room.occupancy_status == "occupied":
            raise ValueError(f"Error: Room {room_number} is currently occupied")

        guest = self._get_reservation_guest(reservation_id, guest_name)
        billing = self._get_reservation_billing(reservation_id)
        if billing is None:
            total_bill = reservation.calculate_total_expected_bill()
            billing = self._create_billing(guest, room, reservation, total_bill)

        room.occupancy_status = "occupied"
        room.current_guests = check_in_names
        room.current_guest = check_in_names[0]

        if vehicle:
            room.vehicle = vehicle
            self.vehicles[vehicle.vehicle_id] = vehicle

        reservation.checked_in_guest_names = check_in_names
        reservation.checked_in = True
        reservation.status = "checked_in"

        return {
            "status": "success",
            "message": f"Guest {guest_name} checked in to room {room_number}",
            "room_number": room_number,
            "billing_id": billing.billing_id,
            "amount_due": billing.amount_due,
            "vehicle": vehicle.vehicle_id if vehicle else "None",
            "guests": check_in_names,
            "reservation_status": reservation.status
        }

    def check_out_guest(self, reservation_id, guest_name, amount_paid=0, night_audit=False, transfer_to_pm=False):
        if reservation_id not in self.reservations:
            raise ValueError(f"Error: Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]
        checked_in_names = list(getattr(reservation, "checked_in_guest_names", []))
        if guest_name not in reservation.guest_names:
            raise ValueError(f"Error: Guest '{guest_name}' is not part of reservation {reservation_id}")

        if reservation.checked_out:
            raise ValueError(f"Error: Guest '{guest_name}' has already been checked out")

        if guest_name not in checked_in_names:
            raise ValueError(f"Error: Guest '{guest_name}' has not checked in yet")
        if amount_paid < 0:
            raise ValueError("Error: Amount paid cannot be negative")
        if night_audit and transfer_to_pm:
            raise ValueError("Error: A bill cannot be settled by night audit and transferred to a PM account at the same time")

        room_number = reservation.room.room_number
        if room_number not in self.rooms:
            raise ValueError(f"Error: Room {room_number} not found")
        room = self.rooms[room_number]

        remaining_guests = [name for name in checked_in_names if name != guest_name]
        if remaining_guests:
            if amount_paid or night_audit or transfer_to_pm:
                raise ValueError(
                    "Error: The room cannot be financially checked out while other registered guests remain checked in"
                )
            reservation.checked_in_guest_names = remaining_guests
            room.current_guests = remaining_guests
            room.current_guest = remaining_guests[0]
            return {
                "status": "success",
                "message": f"Guest {guest_name} departed room {room_number}; room remains occupied",
                "room_number": room_number,
                "guests_remaining": remaining_guests,
                "reservation_status": reservation.status,
            }

        billing_record = self._get_reservation_billing(reservation_id)
        if billing_record is None:
            raise ValueError(f"Error: No billing record found for reservation {reservation_id}")

        proposed_balance = round(billing_record.amount_due - amount_paid, 2)
        if proposed_balance > 0 and not night_audit and not transfer_to_pm:
            raise ValueError(
                f"Error: Outstanding balance of {proposed_balance:.2f} requires night audit settlement or PM account transfer"
            )

        if night_audit:
            if billing_record.balance > 0:
                billing_record.record_payment(billing_record.balance, "Night Audit Settlement")
        elif transfer_to_pm and proposed_balance > 0:
            if amount_paid > 0:
                billing_record.record_payment(amount_paid, "Paid")
            remaining_balance = billing_record.balance
            if remaining_balance <= 0:
                raise ValueError("Error: PM account transfer requires an outstanding balance")
            billing_record.transfer_to_pm_account()
            self.pm_accounts[billing_record.billing_id] = remaining_balance
        elif amount_paid > 0:
            billing_record.record_payment(amount_paid, "Paid")

        vehicle_removed = None
        if room.vehicle:
            vehicle_removed = room.vehicle.vehicle_id
            self.vehicles.pop(vehicle_removed, None)
            room.vehicle = None

        room.occupancy_status = "available"
        room.current_guest = None
        room.current_guests = []
        reservation.checked_in_guest_names = []
        reservation.checked_out = True
        reservation.status = "checked_out"

        if self._room_has_future_reservation(room_number, excluding_reservation_id=reservation_id):
            room.occupancy_status = "reserved"

        return {
            "status": "success",
            "message": f"Guest {guest_name} checked out from room {room_number}",
            "room_number": room_number,
            "billing_id": billing_record.billing_id,
            "amount_due": billing_record.amount_due,
            "amount_paid": billing_record.amount_paid,
            "balance": billing_record.balance,
            "credit": billing_record.credit,
            "pm_account": billing_record.pm_account,
            "vehicle_removed": vehicle_removed if vehicle_removed else "None"
        }

    def run_night_audit(self, audit_datetime, tax_rate):
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

            guest = self._get_reservation_guest(reservation.reservation_id, reservation.guest_names[0])
            room = reservation.room
            room_charge = round(reservation.expected_daily_rate, 2)
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
            room.current_guests = []

            vehicle_removed = None
            if room.vehicle:
                vehicle_removed = room.vehicle.vehicle_id
                self.vehicles.pop(vehicle_removed, None)
                room.vehicle = None

            if self._room_has_future_reservation(room.room_number, excluding_reservation_id=reservation.reservation_id):
                room.occupancy_status = "reserved"

            processed.append({
                "reservation_id": reservation.reservation_id,
                "room_number": room.room_number,
                "status": reservation.status,
                "room_charge": room_charge,
                "tax_amount": tax_amount,
                "amount_due": total_due,
                "billing_id": billing.billing_id,
                "vehicle_removed": vehicle_removed if vehicle_removed else "None"
            })

        return processed
