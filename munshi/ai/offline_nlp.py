"""Offline NLP fallback — rule-based intent classification for common commands.

Used when Claude API is unavailable (no internet).
Handles the most common kirana store commands with regex + keyword matching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Intent:
    name: str
    confidence: float
    params: dict[str, Any] = field(default_factory=dict)


# Amount extraction: handles "300 rupaye", "teen sau", "₹500", "5 sou"
_AMOUNT_PATTERNS = [
    r"₹\s*(\d+(?:\.\d+)?)",
    r"(\d+(?:\.\d+)?)\s*(?:rupay[ae]?|rs\.?|rupe[ey]s?)",
    r"(\d+(?:\.\d+)?)\s*(?:ka|ke|ki)\b",
]

# Keyword maps for intent detection
_SALE_KEYWORDS = {"bika", "biki", "bikaa", "sale", "sell", "becha", "bechi", "sold"}
_EXPENSE_KEYWORDS = {"kharcha", "expense", "kharch", "spend", "diya", "diye", "pay", "paid"}
_UDHAR_KEYWORDS = {"udhar", "credit", "baaki", "udhaar", "khata", "credit", "liya", "le gaya"}
_PAYMENT_KEYWORDS = {"diya", "diye", "returned", "wapas", "payment", "paid back", "chukaya", "chukaya"}
_OUTSTANDING_KEYWORDS = {"kitna", "kitne", "balance", "baaki", "outstanding", "baki", "total"}
_LOCATION_KEYWORDS = {"kahan", "kahaan", "where", "location", "rakhaa", "milega", "kahan hai"}
_STOCK_KEYWORDS = {"stock", "kitna bacha", "inventory", "maal", "kitni", "quantity", "bacha hai"}
_SUMMARY_KEYWORDS = {"summary", "aaj ka", "today", "total", "report", "kitna hua", "aaj kitna"}


def extract_amount(text: str) -> float | None:
    for pattern in _AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    return None


def classify_intent(text: str) -> Intent:
    """
    Fast rule-based intent classification.
    Returns the most likely intent with confidence score.
    """
    text_lower = text.lower().strip()
    words = set(text_lower.split())

    # Check for each intent using keyword overlap
    scores: dict[str, float] = {}

    def keyword_score(keywords: set[str]) -> float:
        matches = words & keywords
        return len(matches) / max(len(keywords), 1) * 10 + (1.0 if matches else 0.0)

    scores["add_sale"] = keyword_score(_SALE_KEYWORDS)
    scores["add_expense"] = keyword_score(_EXPENSE_KEYWORDS)
    scores["add_udhar"] = keyword_score(_UDHAR_KEYWORDS)
    scores["record_payment"] = keyword_score(_PAYMENT_KEYWORDS)
    scores["get_outstanding"] = keyword_score(_OUTSTANDING_KEYWORDS)
    scores["find_product_location"] = keyword_score(_LOCATION_KEYWORDS)
    scores["check_stock"] = keyword_score(_STOCK_KEYWORDS)
    scores["get_daily_summary"] = keyword_score(_SUMMARY_KEYWORDS)

    # Boost sale/expense if an amount is present
    if extract_amount(text_lower):
        scores["add_sale"] += 2.0
        scores["add_expense"] += 1.5
        scores["add_udhar"] += 1.0

    # Resolve ambiguity: payment vs udhar
    # "diya" + customer name → payment; "liya" → udhar
    if "diya" in words or "diye" in words:
        scores["record_payment"] += 2.0
        scores["add_udhar"] -= 1.0
    if "liya" in words or "le" in words:
        scores["add_udhar"] += 2.0

    best_intent = max(scores, key=lambda k: scores[k])
    best_score = scores[best_intent]

    if best_score < 1.5:
        return Intent(name="unknown", confidence=0.0)

    # Normalise confidence to 0-1
    confidence = min(best_score / 10.0, 1.0)

    params: dict[str, Any] = {}
    amount = extract_amount(text_lower)
    if amount is not None:
        params["amount"] = amount

    return Intent(name=best_intent, confidence=confidence, params=params)
