import json
import re

from bs4 import BeautifulSoup


def job_posting(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.string or "{}")
        except json.JSONDecodeError:
            continue
        candidates = payload if isinstance(payload, list) else payload.get("@graph", [payload]) if isinstance(payload, dict) else []
        for item in candidates:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return {}


def plain_text(value: object) -> str:
    return BeautifulSoup(str(value or ""), "html.parser").get_text("\n", strip=True)


def organization_name(value: object) -> str | None:
    if isinstance(value, dict):
        return value.get("name")
    return str(value) if value else None


def location_text(value: object) -> str | None:
    locations = value if isinstance(value, list) else [value]
    parts = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        address = location.get("address", location)
        if isinstance(address, dict):
            parts.extend(str(address.get(key)) for key in ("addressLocality", "addressRegion", "addressCountry") if address.get(key))
    return ", ".join(dict.fromkeys(parts)) or None


def compensation(value: object) -> tuple[float | None, float | None, str | None, str | None]:
    if not isinstance(value, dict):
        return None, None, None, None
    currency = value.get("currency")
    detail = value.get("value", value)
    if not isinstance(detail, dict):
        return None, None, currency, None
    minimum = _number(detail.get("minValue") or detail.get("value"))
    maximum = _number(detail.get("maxValue") or detail.get("value"))
    unit = str(detail.get("unitText", "")).casefold()
    period = "hour" if "hour" in unit else "year" if "year" in unit else "month" if "month" in unit else None
    return minimum, maximum, currency, period


def remote_percentage(posting: dict, text: str) -> int | None:
    if posting.get("jobLocationType") == "TELECOMMUTE" or re.search(r"(full|100\s*%)\s*remote|práca iba z domu|plně na dálku", text, re.I):
        return 100
    if re.search(r"home.?office|remote|práce z domova|prácu z domu", text, re.I):
        return 50
    return None


def _number(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
