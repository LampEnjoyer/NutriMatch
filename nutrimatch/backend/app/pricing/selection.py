"""Pure logic for picking a store product for an ingredient and costing a recipe amount.

No I/O here, so every rule is unit-testable.
"""

import math
from dataclasses import dataclass

from app import units

# Words that describe form or quality rather than identity; product names often omit them.
GENERIC_WORDS = frozenset(
    {"canned", "dried", "dry", "fresh", "frozen", "light", "low", "sodium", "fat", "plain", "nonfat", "large", "cooked"}
)


@dataclass(frozen=True)
class Candidate:
    product_id: str
    description: str
    package_quantity: float | None
    package_unit: str | None
    regular_price: float | None
    promo_price: float | None


def effective_price(regular: float | None, promo: float | None) -> float | None:
    """The price a shopper pays today: the sale price when it's lower than regular."""
    if promo is not None and regular is not None:
        if promo < regular:
            return promo
        return regular
    if regular is not None:
        return regular
    return promo


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().replace("-", " ").replace("®", " ").replace("™", " ").split())


def keyword_groups(normalized_name: str, rules: dict | None) -> list[list[str]]:
    if rules is not None and "require" in rules:
        groups = []
        for group in rules["require"]:
            normalized_group = []
            for word in group:
                normalized_group.append(_normalize_text(word))
            groups.append(normalized_group)
        return groups

    groups = []
    for word in _normalize_text(normalized_name).split():
        if word not in GENERIC_WORDS:
            groups.append([word])
    return groups


def matches_ingredient(description: str, normalized_name: str, rules: dict | None) -> bool:
    text = _normalize_text(description)

    if rules is not None:
        for word in rules.get("exclude", []):
            if _normalize_text(word) in text:
                return False

    for group in keyword_groups(normalized_name, rules):
        found = False
        for word in group:
            # Substring match so "onion" matches "onions" and "egg" matches "eggs".
            if word in text:
                found = True
                break
        if not found:
            return False
    return True


def unit_price(candidate: Candidate) -> tuple[float, str] | None:
    """Price per gram, millilitre or item, plus which of those it is. None if not computable."""
    price = effective_price(candidate.regular_price, candidate.promo_price)
    if price is None:
        return None
    if candidate.package_quantity is None or candidate.package_unit is None:
        return None
    base = units.to_base(candidate.package_quantity, candidate.package_unit)
    if base is None:
        return None
    amount, dimension = base
    if amount <= 0:
        return None
    return price / amount, dimension


def choose_cheapest(candidates: list[Candidate], preferred_dimension: str | None) -> Candidate | None:
    """Cheapest by unit price, comparing only products measured the same way (weight, volume or count).

    Uses the preferred dimension (from the ingredient's usual recipe unit) when any candidate is
    measured that way; otherwise the dimension with the most candidates. Ties go to the lower
    package price, then the lower product id, so the choice is deterministic.
    """
    by_dimension: dict[str, list[tuple[float, float, str, Candidate]]] = {}
    for candidate in candidates:
        priced = unit_price(candidate)
        if priced is None:
            continue
        per_unit, dimension = priced
        package_price = effective_price(candidate.regular_price, candidate.promo_price)
        if dimension not in by_dimension:
            by_dimension[dimension] = []
        by_dimension[dimension].append((per_unit, package_price, candidate.product_id, candidate))

    if len(by_dimension) == 0:
        return None

    chosen_dimension = None
    if preferred_dimension is not None and preferred_dimension in by_dimension:
        chosen_dimension = preferred_dimension
    else:
        most = -1
        # Sort keys so equal counts resolve the same way every time.
        for dimension in sorted(by_dimension):
            if len(by_dimension[dimension]) > most:
                most = len(by_dimension[dimension])
                chosen_dimension = dimension

    ranked = sorted(by_dimension[chosen_dimension], key=lambda entry: (entry[0], entry[1], entry[2]))
    return ranked[0][3]


@dataclass(frozen=True)
class PackageCost:
    packages: int  # whole packages to buy
    shopping_cost: float  # packages x package price
    used_cost: float  # share of the package price for the amount the recipe uses


def package_cost(needed_in_package_units: float, package_quantity: float, package_price: float) -> PackageCost:
    if needed_in_package_units <= 0 or package_quantity <= 0:
        raise ValueError("amounts must be positive")
    ratio = needed_in_package_units / package_quantity
    # Small tolerance so 2.0000000001 packages (float noise) doesn't round up to 3.
    packages = math.ceil(ratio - 1e-9)
    if packages < 1:
        packages = 1
    return PackageCost(
        packages=packages,
        shopping_cost=packages * package_price,
        used_cost=ratio * package_price,
    )
