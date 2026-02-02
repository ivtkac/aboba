"""Utility functions for date and currency parsing."""

import datetime
from typing import Optional

# Ukrainian month mapping for date parsing
UKRAINIAN_MONTH_MAPPING = {
    "січня": 1,
    "лютого": 2,
    "березня": 3,
    "квітня": 4,
    "травня": 5,
    "червня": 6,
    "липня": 7,
    "серпня": 8,
    "вересня": 9,
    "жовтня": 10,
    "листопада": 11,
    "грудня": 12,
}

CURRENCY_INDICATORS = {"грн", "₴"}


def convert_ukrainian_date(date_str: str) -> Optional[str]:
    """
    Convert Ukrainian date string to ISO format (YYYY-MM-DD).

    Expects format: "DD month_name" where month_name is in Ukrainian.
    Example: "15 січня" -> "2024-01-15"

    Args:
        date_str: Date string in Ukrainian format

    Returns:
        ISO format date string or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None

    current_year = datetime.datetime.now().year
    parts = date_str.strip().split()

    if len(parts) != 2:
        return None

    try:
        day = int(parts[0])
        month_name = parts[1].lower()
        month = UKRAINIAN_MONTH_MAPPING.get(month_name)

        if month is None:
            return None

        date_obj = datetime.date(current_year, month, day)
        return date_obj.strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        return None


def contains_currency(text: str) -> bool:
    """
    Check if text contains currency indicators.

    Args:
        text: Text to check

    Returns:
        True if currency indicators are found, False otherwise
    """
    if not text or not isinstance(text, str):
        return False

    return any(indicator in text for indicator in CURRENCY_INDICATORS)
