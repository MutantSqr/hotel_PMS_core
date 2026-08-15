from datetime import datetime, timedelta

from app import HotelAssistant
from app.models import Guest, Reservation, Room, Vehicle


def run_demo():
    """Run a small end-to-end PMS domain demonstration."""
    assistant = HotelAssistant()

    room = Room(
        1501,
        15,
        4,
        ["King Bed", "Ocean View"],
        "presidential",
        "reserved",
        False,
        "",
        False,
    )
    guest = Guest(
        "Demo Guest",
        "demo@example.com",
        "Demo Payment Method",
        "Demo Group",
        "High floor",
        "CONF-DEMO",
    )

    check_in_date = datetime.now()
    check_out_date = check_in_date + timedelta(days=2)
    reservation = Reservation(
        "RES-DEMO",
        [guest.name],
        check_in_date,
        check_out_date,
        room,
        450.0,
        "Extra Towels",
    )
    vehicle = Vehicle(
        "VEH-DEMO",
        "TX-DEMO",
        "Demo",
        "Vehicle",
        "Black",
        guest.name,
        room,
        reservation,
    )

    assistant.add_room(room)
    assistant.add_guest(guest)
    assistant.add_reservation(reservation)

    print("=== Hotel PMS Core Demo ===")
    print("Reservation: RES-DEMO")
    print("Room: 1501 (Presidential Suite)")
    print("Stay: 2 nights")

    print("\n--- Check-In ---")
    print(assistant.check_in_guest("RES-DEMO", guest.name, vehicle=vehicle))

    print("\n--- Check-Out ---")
    print(assistant.check_out_guest("RES-DEMO", guest.name, amount_paid=900.0))


if __name__ == "__main__":
    run_demo()
