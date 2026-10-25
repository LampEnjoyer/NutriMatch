"""Unit conversion scripts for mass, volume, and count measurements.
"""

MASS = "mass"
VOLUME = "volume"
COUNT = "count"

GRAMS_PER_UNIT = {
    "g": 1.0,
    "kg": 1000.0,
    "oz": 28.349523125,
    "lb": 453.59237,
}

MILLILITRES_PER_UNIT = {
    "ml": 1.0,
    "l": 1000.0,
    "tsp": 4.92892159375,
    "tbsp": 14.78676478125,
    "fl_oz": 29.5735295625,
    "cup": 236.5882365,
    # Package sizes only; recipes don't use these.
    "pt": 473.176473,
    "qt": 946.352946,
    "gal": 3785.411784,
}

# "piece" in a recipe and "count" on a package mean the same thing: one whole item.
# clove, slice and pinch are deliberately absent: a "3 ct" garlic package is bulbs, not cloves.
COUNT_UNITS = {"piece", "count"}


def dimension_of(unit: str) -> str | None:
    if unit in GRAMS_PER_UNIT:
        return MASS
    if unit in MILLILITRES_PER_UNIT:
        return VOLUME
    if unit in COUNT_UNITS:
        return COUNT
    return None


def to_base(quantity: float, unit: str) -> tuple[float, str] | None:
    """Return (amount in g / ml / count, dimension), or None for units with no base."""
    if unit in GRAMS_PER_UNIT:
        return quantity * GRAMS_PER_UNIT[unit], MASS
    if unit in MILLILITRES_PER_UNIT:
        return quantity * MILLILITRES_PER_UNIT[unit], VOLUME
    if unit in COUNT_UNITS:
        return quantity, COUNT
    return None


def from_base(amount: float, dimension: str, unit: str) -> float | None:
    if dimension == MASS and unit in GRAMS_PER_UNIT:
        return amount / GRAMS_PER_UNIT[unit]
    if dimension == VOLUME and unit in MILLILITRES_PER_UNIT:
        return amount / MILLILITRES_PER_UNIT[unit]
    if dimension == COUNT and unit in COUNT_UNITS:
        return amount
    return None


def _base_to_dimension(
    amount: float,
    source: str,
    target: str,
    density_g_per_ml: float | None,
    grams_per_count: float | None,
) -> float | None:
    """Move an amount in base units (g / ml / count) to another dimension, if the data allows."""
    if source == target:
        return amount

    if source == VOLUME and target == MASS:
        if density_g_per_ml is None:
            return None
        return amount * density_g_per_ml
    if source == MASS and target == VOLUME:
        if density_g_per_ml is None:
            return None
        return amount / density_g_per_ml

    if source == COUNT and target == MASS:
        if grams_per_count is None:
            return None
        return amount * grams_per_count
    if source == MASS and target == COUNT:
        if grams_per_count is None:
            return None
        return amount / grams_per_count

    if source == COUNT and target == VOLUME:
        grams = _base_to_dimension(amount, COUNT, MASS, density_g_per_ml, grams_per_count)
        if grams is None:
            return None
        return _base_to_dimension(grams, MASS, VOLUME, density_g_per_ml, grams_per_count)
    if source == VOLUME and target == COUNT:
        grams = _base_to_dimension(amount, VOLUME, MASS, density_g_per_ml, grams_per_count)
        if grams is None:
            return None
        return _base_to_dimension(grams, MASS, COUNT, density_g_per_ml, grams_per_count)

    return None


def convert(
    quantity: float,
    from_unit: str,
    to_unit: str,
    density_g_per_ml: float | None = None,
    grams_per_count: float | None = None,
) -> float | None:
    """Convert quantity between units. Returns None when it can't be done reliably."""
    if from_unit == to_unit:
        return quantity

    source = to_base(quantity, from_unit)
    target_dimension = dimension_of(to_unit)
    if source is None or target_dimension is None:
        return None

    amount, source_dimension = source
    moved = _base_to_dimension(amount, source_dimension, target_dimension, density_g_per_ml, grams_per_count)
    if moved is None:
        return None
    return from_base(moved, target_dimension, to_unit)
