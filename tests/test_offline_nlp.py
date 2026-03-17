"""Tests for offline NLP intent classification."""

import pytest

from munshi.ai.offline_nlp import classify_intent, extract_amount


def test_extract_amount_rupaye():
    assert extract_amount("teen sau rupaye ki chai") == 300.0


def test_extract_amount_rs():
    assert extract_amount("rs. 150 ka tel") == 150.0


def test_extract_amount_symbol():
    assert extract_amount("₹500 ka atta") == 500.0


def test_extract_amount_ka():
    assert extract_amount("250 ka doodh") == 250.0


def test_extract_amount_none():
    assert extract_amount("aaj ka summary do") is None


def test_classify_sale():
    intent = classify_intent("teen sau rupaye ki chai biki")
    assert intent.name == "add_sale"
    assert intent.params.get("amount") == 300.0
    assert intent.confidence > 0.3


def test_classify_expense():
    intent = classify_intent("200 rupaye ka kharcha hua bijli bill")
    assert intent.name == "add_expense"
    assert intent.confidence > 0.3


def test_classify_daily_summary():
    intent = classify_intent("aaj ka total kitna hua")
    assert intent.name == "get_daily_summary"


def test_classify_udhar():
    intent = classify_intent("Sharma ji udhar liya")
    assert intent.name == "add_udhar"


def test_classify_unknown():
    intent = classify_intent("kya haal chaal hai")
    assert intent.name == "unknown" or intent.confidence < 0.3
