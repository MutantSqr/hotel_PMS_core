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

    def add_room(self, room):
        self.rooms[room.room_number] = room

    def add_reservation(self, reservation):
        self.reservations[reservation.reservation_id] = reservation

    def add_guest(self, guest):
        self.guests[guest.confirmation_number] = guest

    def check_in_guest(self, reservation_id, guest_name, vehicle=None):
        if reservation_id not in self.reservations:
            raise ValueError(f"Error: Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]

        if guest_name not in reservation.guest_names:
            raise ValueError(f"Error: Guest '{guest_name}' is not part of reservation {reservation_id}")

        room_number = reservation.room.room_number
        if room_number not in self.rooms:
            raise ValueError(f"Error: Room {room_number} not found")

        room = self.rooms[room_number]

        if room.occupancy_status != "reserved":
            raise ValueError(f"Error: Room {room_number} is not reserved for this guest")

        if room.out_of_order:
            raise ValueError(f"Error: Room {room_number} is out of order")

        room.occupancy_status = "occupied"
        room.current_guest = guest_name

        if vehicle:
            room.vehicle = vehicle
            self.vehicles[vehicle.vehicle_id] = vehicle

        reservation.checked_in = True

        total_bill = reservation.calculate_total_expected_bill()
        self.billing_counter += 1
        billing_id = f"BILL{self.billing_counter:04d}"

        guest = next((g for g in self.guests.values() if g.name == guest_name), None)
        if guest is None:
            raise ValueError(f"Error: Guest '{guest_name}' not found in system")

        billing = Billing(
            billing_id=billing_id,
            guest=guest,
            room=room,
            reservation=reservation,
            amount_due=total_bill,
            amount_paid=0,
            balance=total_bill,
            billing_date=datetime.now(),
            payment_method="Pending"
        )

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

        room_number = reservation.room.room_number
        if room_number not in self.rooms:
            raise ValueError(f"Error: Room {room_number} not found")

        room = self.rooms[room_number]

        if room.current_guest != guest_name:
            raise ValueError(f"Error: Guest '{guest_name}' is not currently in room {room_number}")

        vehicle_removed = None
        if room.vehicle:
            vehicle_removed = room.vehicle.vehicle_id
            del self.vehicles[room.vehicle.vehicle_id]
            room.vehicle = None

        room.occupancy_status = "available"
        room.current_guest = None
        reservation.checked_out = True

        billing_record = next(
            (b for b in self.billing_records.values()
             if b.reservation.reservation_id == reservation_id and b.guest.name == guest_name),
            None
        )

        if billing_record is None:
            raise ValueError(f"Error: No billing record found for reservation {reservation_id}")

        billing_record.amount_paid = amount_paid
        billing_record.balance = billing_record.amount_due - amount_paid

        if amount_paid > 0:
            billing_record.payment_method = "Paid"

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