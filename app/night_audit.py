from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")
NIGHT_AUDIT_CUTOFF = time(2, 30)


def money(value):
    try:
        amount = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except Exception as exc:
        raise ValueError("Error: Monetary amount must be a valid number") from exc
    if amount < 0:
        raise ValueError("Error: Monetary amount cannot be negative")
    return amount


def tax_for(amount, tax_rate):
    rate = Decimal(str(tax_rate))
    if rate < 0:
        raise ValueError("Error: Tax rate cannot be negative")
    return (money(amount) * rate).quantize(CENT, rounding=ROUND_HALF_UP)


class NightAuditService:
    """Guarded night-audit operations over the transaction-based folio."""

    @staticmethod
    def no_show_cutoff(reservation):
        return datetime.combine(
            reservation.check_in_date.date() + timedelta(days=1),
            NIGHT_AUDIT_CUTOFF,
        )

    @classmethod
    def is_no_show_eligible(cls, reservation, audit_datetime):
        if reservation.status != "confirmed":
            return False
        if reservation.checked_in or getattr(reservation, "checked_in_guest_names", []):
            return False
        return audit_datetime >= cls.no_show_cutoff(reservation)

    @classmethod
    def process_no_show(cls, reservation, folio, audit_datetime, tax_rate):
        if reservation is None or folio is None:
            raise ValueError("Error: Reservation and folio are required")
        if not cls.is_no_show_eligible(reservation, audit_datetime):
            raise ValueError("Error: Reservation is not eligible for no-show processing")

        room_charge = money(reservation.expected_daily_rate)
        tax_charge = tax_for(room_charge, tax_rate)
        charge_date = cls.no_show_cutoff(reservation)
        base_id = f"{reservation.reservation_id}-NOSHOW"

        # The folio's charge IDs make the operation idempotent. If the room
        # charge already exists, this reservation has already been processed.
        if any(charge.charge_id == f"{base_id}-ROOM" for charge in folio.charges):
            raise ValueError("Error: No-show has already been processed")

        folio.post_charge(
            f"{base_id}-ROOM",
            "No-show room charge",
            room_charge,
            charge_date,
            "no_show_room",
        )
        if tax_charge > 0:
            folio.post_charge(
                f"{base_id}-TAX",
                "No-show tax",
                tax_charge,
                charge_date,
                "no_show_tax",
            )

        reservation.status = "no_show"
        return {
            "status": "success",
            "reservation_id": reservation.reservation_id,
            "room_charge": room_charge,
            "tax_charge": tax_charge,
            "total_charge": room_charge + tax_charge,
            "processed_at": audit_datetime,
        }
