import pytest

from app.pricing.selection import (
    Candidate,
    choose_cheapest,
    effective_price,
    matches_ingredient,
    package_cost,
)


def _candidate(product_id, quantity, unit, regular, promo=None, description="Item"):
    return Candidate(product_id, description, quantity, unit, regular, promo)


def test_effective_price_uses_sale_only_when_lower():
    assert effective_price(4.99, 3.99) == 3.99
    assert effective_price(4.99, 5.49) == 4.99
    assert effective_price(4.99, None) == 4.99
    assert effective_price(None, 2.50) == 2.50
    assert effective_price(None, None) is None


def test_default_matching_requires_identity_words_not_generic_ones():
    assert matches_ingredient("Kroger® Garbanzo Beans", "canned chickpeas", None) is False
    assert matches_ingredient("Kroger Canned Chickpeas 15.5 oz", "canned chickpeas", None) is True
    assert matches_ingredient("Simple Truth Large Brown Eggs", "egg", None) is True
    assert matches_ingredient("Yellow Onions", "yellow onion", None) is True


def test_require_groups_accept_any_alternative():
    rules = {"require": [["chickpea", "chick pea", "garbanzo"]]}
    assert matches_ingredient("Kroger® Garbanzo Beans", "canned chickpeas", rules) is True
    assert matches_ingredient("Kroger® Chick Peas", "canned chickpeas", rules) is True
    assert matches_ingredient("Kroger® Black Beans", "canned chickpeas", rules) is False


def test_exclude_words_reject_lookalikes():
    rules = {"exclude": ["peanut", "almond"]}
    assert matches_ingredient("Kroger Unsalted Butter Sticks", "butter", rules) is True
    assert matches_ingredient("Jif Creamy Peanut Butter", "butter", rules) is False
    egg_rules = {"require": [["egg"]], "exclude": ["eggplant", "egg white"]}
    assert matches_ingredient("Eggplant", "egg", egg_rules) is False
    assert matches_ingredient("Large White Eggs", "egg", egg_rules) is True
    assert matches_ingredient("Liquid Egg Whites", "egg", egg_rules) is False


def test_cheapest_is_by_unit_price_not_sticker_price():
    small = _candidate("small", 8, "oz", 2.49)  # 0.311 per oz
    large = _candidate("large", 32, "oz", 5.99)  # 0.187 per oz
    assert choose_cheapest([small, large], "mass").product_id == "large"


def test_sale_price_counts_toward_cheapest():
    a = _candidate("a", 16, "oz", 4.00)
    b = _candidate("b", 16, "oz", 4.50, promo=3.50)
    assert choose_cheapest([a, b], "mass").product_id == "b"


def test_compares_within_preferred_dimension():
    by_weight = _candidate("weight", 16, "oz", 1.00)
    by_volume = _candidate("volume", 1, "gal", 3.00)
    assert choose_cheapest([by_weight, by_volume], "volume").product_id == "volume"
    assert choose_cheapest([by_weight, by_volume], "mass").product_id == "weight"


def test_falls_back_to_most_common_dimension():
    items = [
        _candidate("w1", 16, "oz", 3.00),
        _candidate("w2", 1, "lb", 2.00),
        _candidate("c1", 12, "count", 1.00),
    ]
    assert choose_cheapest(items, "volume").product_id == "w2"


def test_ties_break_on_package_price_then_product_id():
    same_rate_cheaper_pack = _candidate("b", 8, "oz", 2.00)
    same_rate_bigger_pack = _candidate("a", 16, "oz", 4.00)
    assert choose_cheapest([same_rate_bigger_pack, same_rate_cheaper_pack], "mass").product_id == "b"
    twin_one = _candidate("z", 16, "oz", 4.00)
    twin_two = _candidate("m", 16, "oz", 4.00)
    assert choose_cheapest([twin_one, twin_two], "mass").product_id == "m"


def test_returns_none_when_nothing_is_priced_and_sized():
    no_price = _candidate("a", 16, "oz", None)
    no_size = _candidate("b", None, None, 3.00)
    assert choose_cheapest([no_price, no_size], "mass") is None
    assert choose_cheapest([], "mass") is None


def test_package_cost_rounds_packages_up_and_prorates_used_cost():
    cost = package_cost(needed_in_package_units=12, package_quantity=16, package_price=2.00)
    assert cost.packages == 1
    assert cost.shopping_cost == 2.00
    assert cost.used_cost == pytest.approx(1.50)

    cost = package_cost(needed_in_package_units=20, package_quantity=16, package_price=2.00)
    assert cost.packages == 2
    assert cost.shopping_cost == 4.00


def test_package_cost_ignores_float_noise_at_exact_multiples():
    # 1 lb in oz is 16.000000000000004 after conversion; that must not buy a second package.
    cost = package_cost(needed_in_package_units=32.000000000001, package_quantity=16, package_price=3.00)
    assert cost.packages == 2


def test_package_cost_rejects_non_positive_amounts():
    with pytest.raises(ValueError):
        package_cost(0, 16, 2.00)
