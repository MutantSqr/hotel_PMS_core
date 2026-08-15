from datetime import datetime

from app.assist import HotelAssistant
from app.folio import Folio
from app.models import Guest, Reservation, Room
from app.nightly_posting import NightlyPostingService


def run_demo():
    """Run a small end-to-end hotel PMS demonstration.

    The demo intentionally uses the existing HotelAssistant for operational
    lifecycle rules and the transaction-based Folio for actual financial
    activity. The legacy Billing record remains untouched, so the demo cannot
    accidentally double-post charges while the migration is still in progress.
    """
    pms = HotelAssistant()

    guest = Guest(
        name="Demo Guest",
        contact_details="demo@example.com",
        billing_information="Demo account",
        group_affiliation="",
        special_comments="PMS core demonstration",
        confirmation_number="GUEST-DEMO-001",
    )
    room = Room(
        room_number=101,
        floor_number=1,
        capacity=2,
        amenities=["Wi-Fi"],
        room_type="standard",
        occupancy_status="available",
        out_of_order=False,
        out_of_order_reason="",
        showroom=False,
    )

    arrival = datetime(2026, 8, 12, 15, 0)
    departure = datetime(2026, 8, 13, 11, 0)
    reservation = Reservation(
        reservation_id="RES-DEMO-001",
        guest_names=[guest.name],
        check_in_date=arrival,
        check_out_date=departure,
        room=room,
        expected_daily_rate=150.00,
        special_requests="Demo stay",
    )

    pms.add_room(room)
    pms.add_guest(guest)
    pms.add_reservation(reservation)

    check_in_result = pms.check_in_guest(
        reservation_id=reservation.reservation_id,
        guest_name=guest.name,
        current_datetime=datetime(2026, 8, 12, 15, 5),
    )

    folio = Folio(
        folio_id="FOLIO-DEMO-001",
        reservation_id=reservation.reservation_id,
        guest_name=guest.name,
        room_number=room.room_number,
    )

    audit_result = NightlyPostingService.post_room_night(
        reservation=reservation,
        folio=folio,
        audit_datetime=datetime(2026, 8, 13, 2, 30),
        tax_rate=0.0825,
    )

    folio.record_payment(
        transaction_id="PAY-DEMO-001",
        amount=audit_result["total_charge"],
        payment_method="Demo Card",
        payment_date=datetime(2026, 8, 13, 3, 0),
    )

    checkout_result = pms.check_out_guest(
        reservation_id=reservation.reservation_id,
        guest_name=guest.name,
        amount_paid=0,
        night_audit=True,
    )

    return {
        "check_in": check_in_result,
        "night_audit": audit_result,
        "folio": folio.snapshot(),
        "check_out": checkout_result,
    }


if __name__ == "__main__":
    result = run_demo()
    print("PMS CORE DEMO")
    print("=============")
    print(f"Check-in: {result['check_in']['status']}")
    print(f"Night audit total: ${result['night_audit']['total_charge']:.2f}")
    print(f"Folio balance: ${result['folio']['balance']:.2f}")
    print(f"Check-out: {result['check_out']['status']}")
