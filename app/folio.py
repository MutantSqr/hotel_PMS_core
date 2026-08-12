from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional


CENT = Decimal("0.01")


def money(value) -> Decimal:
    """Normalize a monetary value to cents and reject invalid/negative input."""
    try:
        amount = Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Error: Monetary amount must be a valid number")
    if amount < 0:
        raise ValueError("Error: Monetary amount cannot be negative")
    return amount


@dataclass(frozen=True)
class Charge:
    """An immutable charge posted to a guest folio."""

    charge_id: str
    description: str
    amount: Decimal
    charge_date: datetime
    category: str = "room"

    def __post_init__(self):
        if not self.charge_id or not self.charge_id.strip():
            raise ValueError("Error: Charge ID cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("Error: Charge description cannot be empty")
        object.__setattr__(self, "amount", money(self.amount))
        if self.amount == 0:
            raise ValueError("Error: Charge amount must be greater than zero")
        if not self.category or not self.category.strip():
            raise ValueError("Error: Charge category cannot be empty")


@dataclass(frozen=True)
class Payment:
    """An immutable payment transaction recorded on a guest folio."""

    transaction_id: str
    amount: Decimal
    payment_method: str
    payment_date: datetime

    def __post_init__(self):
        if not self.transaction_id or not self.transaction_id.strip():
            raise ValueError("Error: Payment transaction ID cannot be empty")
        object.__setattr__(self, "amount", money(self.amount))
        if self.amount == 0:
            raise ValueError("Error: Payment amount must be greater than zero")
        if not self.payment_method or not self.payment_method.strip():
            raise ValueError("Error: Payment method cannot be empty")


@dataclass(frozen=True)
class Credit:
    """An immutable credit applied to a guest folio."""

    credit_id: str
    amount: Decimal
    reason: str
    credit_date: datetime

    def __post_init__(self):
        if not self.credit_id or not self.credit_id.strip():
            raise ValueError("Error: Credit ID cannot be empty")
        object.__setattr__(self, "amount", money(self.amount))
        if self.amount == 0:
            raise ValueError("Error: Credit amount must be greater than zero")
        if not self.reason or not self.reason.strip():
            raise ValueError("Error: Credit reason cannot be empty")


class Folio:
    """Guest folio separating expected reservation totals from actual posted activity.

    A reservation's expected total is a forecast. A folio is the authoritative
    transaction ledger for actual charges, payments, and credits. This prevents
    night-audit postings from being added on top of a pre-billed stay total.
    """

    def __init__(self, folio_id, reservation_id, guest_name, room_number):
        if not folio_id or not folio_id.strip():
            raise ValueError("Error: Folio ID cannot be empty")
        if not reservation_id or not reservation_id.strip():
            raise ValueError("Error: Reservation ID cannot be empty")
        if not guest_name or not guest_name.strip():
            raise ValueError("Error: Folio guest name cannot be empty")
        if room_number is None or room_number <= 0:
            raise ValueError("Error: Folio room number must be positive")

        self.folio_id = folio_id
        self.reservation_id = reservation_id
        self.guest_name = guest_name
        self.room_number = room_number
        self.charges = []
        self.payments = []
        self.credits = []
        self.pm_account = False

    @property
    def total_charges(self):
        return sum((charge.amount for charge in self.charges), Decimal("0.00"))

    @property
    def total_payments(self):
        return sum((payment.amount for payment in self.payments), Decimal("0.00"))

    @property
    def total_credits(self):
        return sum((credit.amount for credit in self.credits), Decimal("0.00"))

    @property
    def balance(self):
        return (self.total_charges - self.total_payments - self.total_credits).quantize(CENT)

    @property
    def credit_balance(self):
        return max(Decimal("0.00"), -self.balance).quantize(CENT)

    def post_charge(self, charge_id, description, amount, charge_date=None, category="room"):
        if any(charge.charge_id == charge_id for charge in self.charges):
            raise ValueError(f"Error: Charge {charge_id} has already been posted")
        charge = Charge(charge_id, description, amount, charge_date or datetime.now(), category)
        self.charges.append(charge)
        return charge

    def record_payment(self, transaction_id, amount, payment_method, payment_date=None):
        if any(payment.transaction_id == transaction_id for payment in self.payments):
            raise ValueError(f"Error: Payment transaction {transaction_id} has already been recorded")
        payment = Payment(transaction_id, amount, payment_method, payment_date or datetime.now())
        self.payments.append(payment)
        return payment

    def apply_credit(self, credit_id, amount, reason, credit_date=None):
        if any(credit.credit_id == credit_id for credit in self.credits):
            raise ValueError(f"Error: Credit {credit_id} has already been applied")
        credit = Credit(credit_id, amount, reason, credit_date or datetime.now())
        self.credits.append(credit)
        return credit

    def transfer_to_pm_account(self):
        if self.balance <= 0:
            raise ValueError("Error: Only a positive outstanding balance can be transferred to a PM account")
        self.pm_account = True
        return self.balance

    def assert_integrity(self):
        """Raise if ledger totals contain an impossible negative monetary value."""
        if self.total_charges < 0 or self.total_payments < 0 or self.total_credits < 0:
            raise ValueError("Error: Folio ledger contains an invalid negative total")
        return True

    def snapshot(self):
        """Return a read-only-friendly summary for UI/reporting layers."""
        return {
            "folio_id": self.folio_id,
            "reservation_id": self.reservation_id,
            "guest_name": self.guest_name,
            "room_number": self.room_number,
            "total_charges": self.total_charges,
            "total_payments": self.total_payments,
            "total_credits": self.total_credits,
            "balance": self.balance,
            "credit_balance": self.credit_balance,
            "pm_account": self.pm_account,
        }
