"""Tests for response builder (Hindi/Hinglish spoken responses)."""

import pytest

from munshi.core import response_builder as rb


def test_sale_confirmed_with_description():
    result = rb.sale_confirmed(300.0, "chai")
    assert "chai" in result
    assert "rupaye" in result


def test_sale_confirmed_without_description():
    result = rb.sale_confirmed(500.0)
    assert "rupaye" in result
    assert "sale" in result


def test_udhar_confirmed():
    result = rb.udhar_confirmed("Sharma ji", 200.0, 700.0)
    assert "Sharma ji" in result
    assert "udhar" in result


def test_payment_confirmed_cleared():
    result = rb.payment_confirmed("Ramesh", 500.0, 0.0)
    assert "Ramesh" in result
    assert "saaf" in result


def test_payment_confirmed_remaining():
    result = rb.payment_confirmed("Priya", 200.0, 300.0)
    assert "Priya" in result
    assert "baaki" in result


def test_outstanding_zero():
    result = rb.outstanding_single("Vijay", 0.0)
    assert "nahi" in result.lower()


def test_product_location_with_notes():
    result = rb.product_location("Maggi", "dusre aisle mein", "aisle-2")
    assert "Maggi" in result
    assert "dusre aisle" in result


def test_daily_summary_profit():
    result = rb.daily_summary(5000.0, 1000.0, 4000.0, 10)
    assert "fayda" in result
    assert "10" in result


def test_daily_summary_loss():
    result = rb.daily_summary(500.0, 800.0, -300.0, 5)
    assert "nuksan" in result
