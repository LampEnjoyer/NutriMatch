import pytest

from app.units import convert, dimension_of


def test_exact_mass_conversions():
    assert convert(1, "lb", "oz") == pytest.approx(16)
    assert convert(1, "kg", "g") == 1000
    assert convert(1, "lb", "g") == pytest.approx(453.59237)


def test_exact_volume_conversions():
    assert convert(1, "cup", "tbsp") == pytest.approx(16)
    assert convert(1, "tbsp", "tsp") == pytest.approx(3)
    assert convert(1.5, "cup", "fl_oz") == pytest.approx(12)
    assert convert(1, "gal", "cup") == pytest.approx(16)
    assert convert(0.5, "gal", "qt") == pytest.approx(2)


def test_mass_volume_needs_density():
    assert convert(3, "tbsp", "oz") is None
    grams = convert(1, "cup", "g", density_g_per_ml=0.5)
    assert grams == pytest.approx(236.5882365 * 0.5)


def test_count_conversions():
    assert convert(2, "piece", "count") == 2
    assert convert(2, "piece", "lb") is None
    assert convert(2, "piece", "g", grams_per_count=110) == pytest.approx(220)
    # A "3 ct" garlic package is bulbs, so cloves never convert to counts.
    assert convert(3, "clove", "count") is None
    assert dimension_of("clove") is None


def test_unknown_units_return_none():
    assert convert(1, "handful", "g") is None
    assert convert(1, "g", "handful") is None
