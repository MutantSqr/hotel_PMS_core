from datetime import datetime


class Guest:
    def __init__(self, name, contact_details, billing_information, group_affiliation, special_comments,
                 confirmation_number):
        if not name or not name.strip():
            raise ValueError("Error: Guest name cannot be empty")
        if not contact_details or not contact_details.strip():
            raise ValueError("Error: Contact details cannot be empty")
        if not confirmation_number or not confirmation_number.strip():
            raise ValueError("Error: Confirmation number cannot be empty")

        self.name = name
        self.contact_details = contact_details
        self.billing_information = billing_information
        self.group_affiliation = group_affiliation
        self.special_comments = special_comments
        self.confirmation_number = confirmation_number


class Room:
    def __init__(self, room_number, floor_number, capacity, amenities, room_type, occupancy_status, out_of_order,
                 out_of_order_reason, showroom):
        if not room_number or room_number <= 0:
            raise ValueError("Error: Room number must be a positive number")
        if floor_number < 1 or floor_number > 15:
            raise ValueError("Error: Floor number must be between 1 and 15")
        if capacity <= 0:
            raise ValueError("Error: Room capacity must be positive")
        if room_type not in ["standard", "presidential"]:
            raise ValueError("Error: Room type must be 'standard' or 'presidential'")
        if occupancy_status not in ["available", "occupied", "reserved"]:
            raise ValueError("Error: Occupancy status must be 'available', 'occupied', or 'reserved'")
        if out_of_order and (not out_of_order_reason or not out_of_order_reason.strip()):
            raise ValueError("Error: If room is out of order, a reason must be provided")
        if room_type == "presidential" and floor_number != 15:
            raise ValueError("Error: Presidential suite must be on floor 15")

        self.room_number = room_number
        self.floor_number = floor_number
        self.capacity = capacity
        self.amenities = amenities
        self.room_type = room_type
        self.occupancy_status = occupancy_status
        self.out_of_order = out_of_order
        self.out_of_order_reason = out_of_order_reason
        self.showroom = showroom
        self.current_guest = None
        self.vehicle = None


class Reservation:
    def __init__(self, reservation_id, guest_names, check_in_date, check_out_date, room, expected_daily_rate,
                 special_requests):
        if not reservation_id or not reservation_id.strip():
            raise ValueError("Error: Reservation ID cannot be empty")
        if not guest_names or len(guest_names) == 0:
            raise ValueError("Error: At least one guest name is required")
        if check_in_date >= check_out_date:
            raise ValueError("Error: Check-out date must be after check-in date")
        if expected_daily_rate <= 0:
            raise ValueError("Error: Expected daily rate must be positive")
        if room is None:
            raise ValueError("Error: Reservation must be linked to a room")

        self.reservation_id = reservation_id
        self.guest_names = guest_names
        self.check_in_date = check_in_date
        self.check_out_date = check_out_date
        self.room = room
        self.expected_daily_rate = expected_daily_rate
        self.special_requests = special_requests
        self.checked_in = False
        self.checked_out = False

    def calculate_length_of_stay(self):
        return (self.check_out_date - self.check_in_date).days

    def calculate_total_expected_bill(self):
        return self.calculate_length_of_stay() * self.expected_daily_rate


class Vehicle:
    def __init__(self, vehicle_id, license_plate, make, model, color, guest_name, room, reservation):
        if guest_name not in reservation.guest_names:
            raise ValueError(f"Error: Guest '{guest_name}' is not part of reservation {reservation.reservation_id}")
        if room.room_number != reservation.room.room_number:
            raise ValueError(
                f"Error: Room {room.room_number} does not match reservation room {reservation.room.room_number}")
        if not vehicle_id or not license_plate:
            raise ValueError("Error: Vehicle ID and license plate cannot be empty")

        self.vehicle_id = vehicle_id
        self.license_plate = license_plate
        self.make = make
        self.model = model
        self.color = color
        self.guest_name = guest_name
        self.room = room
        self.reservation = reservation


class Billing:
    """
    FIX: balance is now a derived @property instead of a stored value the
    caller had to compute and pass in. It is mathematically impossible for
    it to drift out of sync with amount_due / amount_paid now, which is what
    the README's "auto-calculated ledger balances" claim was actually
    supposed to mean.
    """

    def __init__(self, billing_id, guest, room, reservation, amount_due, amount_paid, billing_date,
                 payment_method):
        if not billing_id or not billing_id.strip():
            raise ValueError("Error: Billing ID cannot be empty")
        if guest is None:
            raise ValueError("Error: Billing must be linked to a guest")
        if room is None:
            raise ValueError("Error: Billing must be linked to a room")
        if amount_due < 0:
            raise ValueError("Error: Amount due cannot be negative")
        if amount_paid < 0:
            raise ValueError("Error: Amount paid cannot be negative")
        if not payment_method or not payment_method.strip():
            raise ValueError("Error: Payment method cannot be empty")

        self.billing_id = billing_id
        self.guest = guest
        self.room = room
        self.reservation = reservation
        self.amount_due = amount_due
        self._amount_paid = amount_paid
        self.billing_date = billing_date
        self.payment_method = payment_method

    @property
    def amount_paid(self):
        return self._amount_paid

    @amount_paid.setter
    def amount_paid(self, value):
        if value < 0:
            raise ValueError("Error: Amount paid cannot be negative")
        self._amount_paid = value

    @property
    def balance(self):
        return self.amount_due - self._amount_paid
