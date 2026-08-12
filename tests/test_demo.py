from decimal import Decimal

from app.demo import run_demo


def test_demo_runs_from_check_in_through_night_audit_and_checkout():
    result = run_demo()

    assert result["check_in"]["status"] == "success"
    assert result["night_audit"]["status"] == "success"
    assert result["folio"]["total_charges"] == Decimal("162.38")
    assert result["folio"]["total_payments"] == Decimal("162.38")
    assert result["folio"]["balance"] == Decimal("0.00")
    assert result["check_out"]["status"] == "success"
