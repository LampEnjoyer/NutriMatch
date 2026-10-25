"""Parse retailer package-size text such as "1/2 gal", "16 oz", "32 fl oz", "12 ct"."""

import re
from dataclasses import dataclass

# Longest aliases first so "fl oz" wins over "oz" and "lbs" over "lb".
_UNIT_ALIASES = [
    ("fl. oz", "fl_oz"),
    ("fl oz", "fl_oz"),
    ("floz", "fl_oz"),
    ("ounces", "oz"),
    ("ounce", "oz"),
    ("oz", "oz"),
    ("pounds", "lb"),
    ("pound", "lb"),
    ("lbs", "lb"),
    ("lb", "lb"),
    ("kilograms", "kg"),
    ("kg", "kg"),
    ("grams", "g"),
    ("gram", "g"),
    ("g", "g"),
    ("millilitres", "ml"),
    ("milliliters", "ml"),
    ("ml", "ml"),
    ("liters", "l"),
    ("litres", "l"),
    ("liter", "l"),
    ("litre", "l"),
    ("l", "l"),
    ("gallons", "gal"),
    ("gallon", "gal"),
    ("gal", "gal"),
    ("quarts", "qt"),
    ("quart", "qt"),
    ("qt", "qt"),
    ("pints", "pt"),
    ("pint", "pt"),
    ("pt", "pt"),
    ("count", "count"),
    ("ct", "count"),
    ("each", "count"),
    ("ea", "count"),
]

_NUMBER = r"(\d+\s+\d+/\d+|\d+/\d+|\d*\.\d+|\d+)"


@dataclass(frozen=True)
class PackageSize:
    quantity: float
    unit: str  # one of app.units' mass, volume or count units


def _parse_number(text: str) -> float | None:
    text = text.strip()
    if " " in text:
        whole_text, fraction_text = text.split(None, 1)
        whole = _parse_number(whole_text)
        fraction = _parse_number(fraction_text)
        if whole is None or fraction is None:
            return None
        return whole + fraction
    if "/" in text:
        numerator_text, denominator_text = text.split("/", 1)
        denominator = float(denominator_text)
        if denominator == 0:
            return None
        return float(numerator_text) / denominator
    return float(text)


def _match_unit(rest: str) -> str | None:
    rest = rest.strip().lower()
    for alias, unit in _UNIT_ALIASES:
        if rest == alias or rest == alias + ".":
            return unit
    return None


def parse_size(raw: str | None) -> PackageSize | None:
    """Parse a single package size. Multi-part sizes ("6 ct / 12 oz") use the first part."""
    if raw is None:
        return None
    text = raw.strip().lower()
    if text == "":
        return None

    # "6 ct / 12 oz" or "2 x 8 oz": too ambiguous to split reliably; take the first segment only.
    first = text.split("/ ")[0].split(" x ")[0].strip()

    match = re.fullmatch(_NUMBER + r"\s*(.+)", first)
    if match is None:
        return None

    quantity = _parse_number(match.group(1))
    unit = _match_unit(match.group(2))
    if quantity is None or unit is None or quantity <= 0:
        return None
    return PackageSize(quantity=quantity, unit=unit)
