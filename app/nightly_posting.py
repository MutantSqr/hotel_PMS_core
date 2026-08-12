from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def money(value):
    try:
        amount = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except Exception as exc:
        raise ValueError("Error: Monetary amount must be a valid number") from exc
    if amount <= 0:
        raise ValueError("Error: Monetary amount must be greater than zero") from None
    return amount


def tax_for(amount, tax_rate):
    try:
        rate = Decimal(str(tax_rate))
    except Exception as exc:
        raise ValueError("Error: Tax rate must be a valid number") from exc
    if rate < 0:
        raise ValueError("Error: Tax rate cannot be negative")
    return (money(amount) * rate).quantize(CENT, rounding=ROUND_HALF_UP)


class NightlyPostingService:
    """Guarded posting of one actual room night and its tax to a folio."""

    @staticmethod
    def _stay_date(reservation):
        value = reservation.check_in_date
        return value.date() if isinstance(value, datetime) else value

    @classmethod
    def _charge_prefix(cls, reservation, stay_date):
        return f"{reservation.reservation_id}-ROOMNIGHT-{stay_date.isoformat()}"

    @classmethod
    def post_room_night(cls, reservation, folio, audit_datetime, tax_rate):
        if reservation is None or folio is None:
            raise ValueError("Error: Reservation and folio are required")
        if not isinstance(audit_datetime, datetime):
            raise ValueError("Error: Audit timestamp is required")
        if reservation.status != "checked_in" or not getattr(reservation, "checked_in", False):
            raise ValueError("Error: Only checked-in reservations can receive nightly charges")

        stay_date = cls._stay_date(reservation)
        if audit_datetime.date() < stay_date:
            raise ValueError("Error: Cannot post a room night before arrival")
        if audit_datetime.date() >= reservation.check_out_date.date():
            raise ValueError("Error: Cannot post a room night on or after departure")

        room_charge = money(reservation.expected_daily_rate)
        tax_charge = tax_for(room_charge, tax_rate)
        prefix = cls._charge_prefix(reservation, stay_date)
        room_id = f"{prefix}-ROOM"
        tax_id = f"{prefix}-TAX"

        if any(charge.charge_id == room_id for charge in folio.charges):
            raise ValueError("Error: Room night has already been posted")
        if tax_charge > 0 and any(charge.charge_id == tax_id for charge in folio.charges):
            raise ValueError("Error: Room-night tax has already been posted")

        charge_date = datetime.combine(stay_date, audit_datetime.time())
        folio.post_charge(room_id, "Nightly room charge", room_charge, charge_date, "room_night")
        if tax_charge > 0:
            folio.post_charge(tax_id, "Nightly room tax", tax_charge, charge_date, "room_tax")

        return {
            "status": "success",
            "reservation_id": reservation.reservation_id,
            "stay_date": stay_date,
            "room_charge": room_charge,
            "tax_charge": tax_charge,
            "total_charge": room_charge + tax_charge,
            "processed_at": audit_datetime,
        }
