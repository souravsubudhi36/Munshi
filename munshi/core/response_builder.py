"""Formats structured data into natural spoken Hindi/Hinglish responses."""

from __future__ import annotations

from datetime import date

from num2words import num2words


def rupees(amount: float) -> str:
    """Convert a float amount to spoken Indian rupees string.
    e.g. 300 → 'teen sau rupaye', 1500 → 'ek hazaar paanch sau rupaye'
    """
    try:
        # num2words Hindi with Indian numbering
        words = num2words(int(amount), lang="hi", to="cardinal")
        return f"{words} rupaye"
    except Exception:
        return f"{int(amount)} rupaye"


def sale_confirmed(amount: float, description: str | None = None) -> str:
    amt = rupees(amount)
    if description:
        return f"{amt} ka {description} note kar liya."
    return f"{amt} ka sale note kar liya."


def expense_confirmed(amount: float, description: str | None = None) -> str:
    amt = rupees(amount)
    if description:
        return f"{amt} ka {description} kharcha likh diya."
    return f"{amt} ka kharcha note kar liya."


def udhar_confirmed(customer_name: str, amount: float, outstanding: float) -> str:
    amt = rupees(amount)
    total = rupees(outstanding)
    return f"{customer_name} ka {amt} udhar likh diya. Ab kul {total} baaki hai."


def payment_confirmed(customer_name: str, amount: float, remaining: float) -> str:
    amt = rupees(amount)
    if remaining <= 0:
        return f"{customer_name} ne {amt} diye. Unka udhar saaf ho gaya!"
    rem = rupees(remaining)
    return f"{customer_name} ne {amt} diye. Ab {rem} baaki hai."


def outstanding_single(customer_name: str, amount: float) -> str:
    if amount <= 0:
        return f"{customer_name} ka koi udhar nahi hai."
    return f"{customer_name} ka {rupees(amount)} baaki hai."


def outstanding_all(entries: list[dict]) -> str:
    if not entries:
        return "Kisi ka udhar nahi hai."
    parts = [f"{e['customer_name']}: {rupees(e['outstanding_amount'])}" for e in entries[:5]]
    summary = ", ".join(parts)
    if len(entries) > 5:
        summary += f" aur {len(entries) - 5} aur log."
    return f"Udhar wale log: {summary}"


def product_location(product_name: str, location_notes: str | None, shelf: str | None) -> str:
    if location_notes:
        return f"{product_name} {location_notes} mein hai."
    if shelf:
        return f"{product_name} {shelf} par hai."
    return f"{product_name} ki location set nahi hai. Inventory mein update karo."


def stock_level(product_name: str, quantity: float, unit: str = "piece") -> str:
    qty_words = num2words(int(quantity), lang="hi", to="cardinal") if quantity > 0 else "khatam"
    if quantity <= 0:
        return f"{product_name} ka stock khatam ho gaya hai."
    return f"{product_name} ka {qty_words} {unit} stock bacha hai."


def daily_summary(total_sales: float, total_expenses: float, net: float, count: int) -> str:
    sales = rupees(total_sales)
    expenses = rupees(total_expenses)
    profit = rupees(abs(net))
    direction = "fayda" if net >= 0 else "nuksan"
    return (
        f"Aaj {count} transactions hue. "
        f"Total sale {sales}, kharcha {expenses}. "
        f"Net {direction}: {profit}."
    )


def error_not_understood() -> str:
    return "Samajh nahi aaya, phir se bolo."


def error_customer_not_found(name: str) -> str:
    return f"'{name}' naam ka customer nahi mila. Naya banaaun?"


def error_product_not_found(name: str) -> str:
    return f"'{name}' maal inventory mein nahi hai."


def ambiguous_customer(candidates: list[str]) -> str:
    names = " ya ".join(candidates[:3])
    return f"Kaun sa? {names}?"
