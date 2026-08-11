from datetime import datetime, timedelta
from app.models import Room, Guest, Reservation, Vehicle
from app.assistant import HotelAssistant


def run_demo():
    assistant = HotelAssistant()

    # 1. Initialize System Components
    room = Room(1501, 15, 4, ["King Bed", "Ocean View"], "presidential", "reserved", False, "", False)
    guest = Guest("Rondrick Bowser", "rondrick@example.com", "Visa ending 4242", "Vanguard Fleet", "High floor",
                  "CONF999")

    check_in_date = datetime.now()
    check_out_date = check_in_date + timedelta(days=2)
    reservation = Reservation("RES999", ["Rondrick Bowser"], check_in_date, check_out_date, room, 450.0, "Extra Towels")

    vehicle = Vehicle("VEH01", "TX-8890", "Buick", "Enclave", "Black", "Rondrick Bowser", room, reservation)

    # 2. Register with State Assistant
    assistant.add_room(room)
    assistant.add_guest(guest)
    assistant.add_reservation(reservation)

    # 3. Simulate Operations
    print("--- Executing Check-In Telemetry ---")
    check_in_telemetry = assistant.check_in_guest("RES999", "Rondrick Bowser", vehicle=vehicle)
    print(check_in_telemetry)

    print("\n--- Executing Check-Out Telemetry ---")
    check_out_telemetry = assistant.check_out_guest("RES999", "Rondrick Bowser", amount_paid=900.0)
    print(check_out_telemetry)


if __name__ == "__main__":
    run_demo()