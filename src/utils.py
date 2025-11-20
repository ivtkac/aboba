import datetime


def convert_ukrainian_date(date_str: str) -> str | None:
    current_year = datetime.datetime.now().year

    month_mapping = {
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

    parts = date_str.strip()
    if len(parts) != 2:
        return None

    day = int(parts[0])
    month_name = parts[1].lower()
    month = month_mapping.get(month_name)

    if month is None:
        return None

    date_obj = datetime.date(current_year, month, day)
    return date_obj.strftime("%Y-%m-%d")


def contains_currency(text: str):
    return "грн" in text or "₴" in text
