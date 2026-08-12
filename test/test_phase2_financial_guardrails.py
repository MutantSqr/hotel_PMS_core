import pytest

from app.models import Billing, Guest, Room, Reservation
from datetime import datetime, timedelta


def make_billing():
    guest = Guest("Financial Guardrail Guest", "billing@example.com", "redacted", "", "", "FIN-GUEST")
    room = Room(1501, 15, 2, ["King Bed"], "presidential", "available", False, "", False)
    reservation = Reservation(
        "FIN-RES",
        [guest.name],
        datetime(2026, 8, 11, 15, 0),
        datetime(2026, 8, 12, 11, 0),
        room,
        300.00,
        "",
    )
    return Billing(
        billing_id="FIN-BILL",
        guest=guest,
        room=room,
        reservation=reservation,
        amount_due=300.00,
        amount_paid=0,
        billing_date=datetime(2026, 8, 11, 15, 0),
        payment_method="Pending",
        tax_amount=0,
    )


def test_billing_rejects_negative_amounts():
    billing = make_billing()
    with pytest.raises(ValueError, match="Payment amount must be greater than zero"):
        billing.record_payment(-1, "Cash")
    with pytest.raises(ValueError, match="Payment amount must be greater than zero"):
        billing.record_payment(0, "Cash")
    assert billing.amount_paid == 0
    assert billing.payment_transactions == []


def test_billing_rejects_blank_payment_method():
    billing = make_billing()
    with pytest.raises(ValueError, match="Payment method cannot be empty"):
        billing.record_payment(100, "   ")
    assert billing.amount_paid == 0
    assert billing.payment_transactions == []


def test_billing_rejects_negative_credit():
    billing = make_billing()
    with pytest.raises(ValueError, match="Credit cannot be negative"):
        billing.apply_credit(-25)
    assert billing.amount_paid == 0
    assert billing.payment_transactions == []


def test_billing_ledger_is_the_only_source_of_payment_total():
    billing = make_billing()
    billing.record_payment(100, "Cash")
    billing.record_payment(50, "Card")
    assert billing.amount_paid == 150
    assert round(sum(item["amount"] for item in billing.payment_transactions), 2) == 150
    assert billing.balance == 150


def test_billing_credit_is_derived_not_manually_set():
    billing = make_billing()
    billing.record_payment(350, "Card")
    assert billing.balance == -50
    assert billing.credit == 50


def test_night_audit_rejects_invalid_tax_rate_and_early_run():
    from app.assist import HotelAssistant

    assistant = HotelAssistant()
    with pytest.raises(ValueError, match="cannot run before 2:30 AM"):
        assistant.run_night_audit(datetime(2026, 8, 12, 2, 29), 0.15)
    with pytest.raises(ValueError, match="Tax rate must be between 0 and 1"):
        assistant.run_night_audit(datetime(2026, 8, 12, 2, 30), -0.01)
    with pytest.raises(ValueError, match="Tax rate must be between 0 and 1"):
        assistant.run_night_audit(datetime(2026, 8, 12, 2, 30), 1.01)


def test_night_audit_does_not_process_future_arrivals():
    from app.assist import HotelAssistant

    assistant = HotelAssistant()
    guest = Guest("Future Arrival", "future@example.com", "redacted", "", "", "FUTURE-GUEST")
    room = Room(1501, 15, 2, ["King Bed"], "presidential", "available", False, "", False)
    assistant.add_guest(guest)
    assistant.add_room(room)
    future_start = datetime(2026, 8, 13, 15, 0)
    reservation = Reservation(
        "FUTURE-RES",
        [guest.name],
        future_start,
        future_start + timedelta(days=1),
        room,
        300,
        "",
    )
    assistant.add_reservation(reservation)

    result = assistant.run_night_audit(datetime(2026, 8, 12, 2, 30), 0.15)

    assert result == []
    assert reservation.status == "confirmed"
    assert len(assistant.billing_records) == 0
