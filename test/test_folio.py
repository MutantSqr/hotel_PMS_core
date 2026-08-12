from datetime import datetime
from decimal import Decimal

import pytest

from app.folio import Folio


def make_folio():
    return Folio("FOL001", "RES001", "Jane Doe", 1501)


def test_reservation_expected_total_is_not_a_folio_charge():
    folio = make_folio()
    folio.post_charge("CHG001", "Room night 1", "150.00", datetime(2026, 8, 12), "room")
    assert folio.total_charges == Decimal("150.00")
    assert folio.balance == Decimal("150.00")


def test_multiple_nightly_charges_accumulate_without_prebilling():
    folio = make_folio()
    folio.post_charge("CHG001", "Room night 1", 150, category="room")
    folio.post_charge("CHG002", "Room night 2", 150, category="room")
    assert folio.total_charges == Decimal("300.00")


def test_duplicate_charge_id_is_rejected():
    folio = make_folio()
    folio.post_charge("CHG001", "Room night 1", 150)
    with pytest.raises(ValueError, match="already been posted"):
        folio.post_charge("CHG001", "Duplicate", 150)


def test_duplicate_payment_transaction_is_rejected():
    folio = make_folio()
    folio.post_charge("CHG001", "Room night", 150)
    folio.record_payment("PAY001", 150, "Card")
    with pytest.raises(ValueError, match="already been recorded"):
        folio.record_payment("PAY001", 150, "Card")


def test_payment_reduces_balance():
    folio = make_folio()
    folio.post_charge("CHG001", "Room night", 150)
    folio.record_payment("PAY001", 100, "Card")
    assert folio.balance == Decimal("50.00")


def test_overpayment_becomes_credit_balance():
    folio = make_folio()
    folio.post_charge("CHG001", "Room night", 150)
    folio.record_payment("PAY001", 200, "Card")
    assert folio.balance == Decimal("-50.00")
    assert folio.credit_balance == Decimal("50.00")


def test_credit_reduces_amount_owed_without_creating_a_negative_charge():
    folio = make_folio()
    folio.post_charge("CHG001", "Room night", 150)
    folio.apply_credit("CRD001", 25, "Service recovery")
    assert folio.total_credits == Decimal("25.00")
    assert folio.balance == Decimal("125.00")


def test_duplicate_credit_id_is_rejected():
    folio = make_folio()
    folio.apply_credit("CRD001", 25, "Service recovery")
    with pytest.raises(ValueError, match="already been applied"):
        folio.apply_credit("CRD001", 25, "Duplicate")


def test_negative_money_is_rejected():
    folio = make_folio()
    with pytest.raises(ValueError, match="cannot be negative"):
        folio.post_charge("CHG001", "Invalid", -1)
    with pytest.raises(ValueError, match="cannot be negative"):
        folio.record_payment("PAY001", -1, "Card")
    with pytest.raises(ValueError, match="cannot be negative"):
        folio.apply_credit("CRD001", -1, "Invalid")


def test_pm_transfer_requires_positive_outstanding_balance():
    folio = make_folio()
    folio.post_charge("CHG001", "Room night", 150)
    assert folio.transfer_to_pm_account() == Decimal("150.00")
    assert folio.pm_account is True


def test_pm_transfer_rejects_settled_folio():
    folio = make_folio()
    folio.post_charge("CHG001", "Room night", 150)
    folio.record_payment("PAY001", 150, "Card")
    with pytest.raises(ValueError, match="positive outstanding balance"):
        folio.transfer_to_pm_account()


def test_folio_integrity_and_snapshot():
    folio = make_folio()
    folio.post_charge("CHG001", "Room night", 150)
    folio.record_payment("PAY001", 100, "Card")
    assert folio.assert_integrity() is True
    snapshot = folio.snapshot()
    assert snapshot["balance"] == Decimal("50.00")
    assert snapshot["reservation_id"] == "RES001"
