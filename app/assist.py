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
        self.pm_accounts = {}
        self._reservation_guest_map = {}

    def add_room(self, room):
        if room.room_number in self.rooms:
            raise ValueError(f"Error: Room {room.room_number} already exists")
        self.rooms[room.room_number] = room

    def add_reservation(self, reservation):
        if reservation.reservation_id in self.reservations:
            raise ValueError(f"Error: Reservation {reservation.reservation_id} already exists")

        room = reservation.room
        if room.room_number not in self.rooms:
            raise ValueError(f"Error: Room {room.room_number} is not registered in the system")

        if room.out_of_order:
            raise ValueError(f"Error: Room {room.room_number} is out of order and cannot be reserved")

        if room.occupancy_status != "available":
            raise ValueError(f"Error: Room {room.room_number} is unavailable for reservation")

        # One active reservation per room. A checked-out reservation remains
        # in the history, but it no longer blocks the room.
        for existing in self.reservations.values():
            if existing.room.room_number == room.room_number and not existing.checked_out:
                raise ValueError(f"Error: Room {room.room_number} already has an active reservation")

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

        # All validation happens before either registry or room state changes.
        self.reservations[reservation.reservation_id] = reservation
        self._reservation_guest_map[reservation.reservation_id] = guest_map
        room.occupancy_status = "reserved"

    def add_guest(self, guest):
        if guest.confirmation_number in self.guests:
            raise ValueError(f"Error: Guest with confirmation {guest.confirmation_number} already exists")
        self.guests[guest.confirmation_number] = guest

    def check_in_guest(self, reservation_id, guest_name, vehicle=None, accompanying_guest_names=None):
        if reservation_id not in self.reservations:
            raise ValueError(f"Error: Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]

        if guest_name not in reservation.guest_names:
            raise ValueError(f"Error: Guest '{guest_name}' is not part of reservation {reservation_id}")

        if reservation.checked_in:
            raise ValueError(f"Error: Reservation {reservation_id} has already been checked in")

        room_number = reservation.room.room_number
        if room_number not in self.rooms:
            raise ValueError(f"Error: Room {room_number} not found")

        room = self.rooms[room_number]

        if room.occupancy_status != "reserved":
            raise ValueError(f"Error: Room {room_number} is not reserved for this guest")

        if room.out_of_order:
            raise ValueError(f"Error: Room {room_number} is out of order")

        accompanying_guest_names = accompanying_guest_names or []
        check_in_names = [guest_name] + accompanying_guest_names

        if len(check_in_names) > room.capacity:
            raise ValueError(f"Error: Room {room_number} can accommodate only {room.capacity} guests")

        if len(set(check_in_names)) != len(check_in_names):
            raise ValueError("Error: A guest cannot be checked in more than once")

        for name in check_in_names:
            if name not in reservation.guest_names:
                raise ValueError(f"Error: Guest '{name}' is not part of reservation {reservation_id}")
            if name not in self._reservation_guest_map[reservation_id]:
                raise ValueError(f"Error: Guest '{name}' is not registered in the system")

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
        room.current_guests = check_in_names

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
            "vehicle": vehicle.vehicle_id if vehicle else "None",
            "guests": check_in_names
        }

    def check_out_guest(self, reservation_id, guest_name, amount_paid=0,
                        night_audit=False, transfer_to_pm=False):
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

        if night_audit and transfer_to_pm:
            raise ValueError("Error: A bill cannot be settled by night audit and transferred to a PM account at the same time")

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

        # Validate payment and outstanding-balance rules before changing room
        # or reservation state. Overpayment is allowed and becomes a credit.
        billing_record.amount_paid = amount_paid
        balance = billing_record.balance

        if balance > 0 and not night_audit and not transfer_to_pm:
            raise ValueError(
                f"Error: Outstanding balance of {balance:.2f} requires night audit settlement or PM account transfer"
            )

        if night_audit and balance > 0:
            billing_record.amount_paid = billing_record.amount_due
            billing_record.payment_method = "Night Audit Settlement"
        elif transfer_to_pm and balance > 0:
            billing_record.transfer_to_pm_account()
            self.pm_accounts[billing_record.billing_id] = billing_record.balance
        elif amount_paid > 0:
            billing_record.payment_method = "Paid"

        vehicle_removed = None
        if room.vehicle:
            vehicle_removed = room.vehicle.vehicle_id
            del self.vehicles[vehicle_removed]
            room.vehicle = None

        room.occupancy_status = "available"
        room.current_guest = None
        room.current_guests = []
        reservation.checked_out = True

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
