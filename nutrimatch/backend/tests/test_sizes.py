import pytest

from app.pricing.sizes import PackageSize, parse_size


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("16 oz", PackageSize(16, "oz")),
        ("8 OZ", PackageSize(8, "oz")),
        ("32 fl oz", PackageSize(32, "fl_oz")),
        ("16.9 fl oz", PackageSize(16.9, "fl_oz")),
        ("1/2 gal", PackageSize(0.5, "gal")),
        ("1 gal", PackageSize(1, "gal")),
        ("1 pt", PackageSize(1, "pt")),
        ("1 lb", PackageSize(1, "lb")),
        ("3 lbs", PackageSize(3, "lb")),
        ("1 1/2 lb", PackageSize(1.5, "lb")),
        (".5 lb", PackageSize(0.5, "lb")),
        ("500 g", PackageSize(500, "g")),
        ("12 ct", PackageSize(12, "count")),
        ("1 each", PackageSize(1, "count")),
        ("6 ct / 12 oz", PackageSize(6, "count")),
    ],
)
def test_parses_common_sizes(raw, expected):
    assert parse_size(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "each", "bunch", "0 oz", "2 x 8 oz", "family size", "1/0 lb"])
def test_unparseable_sizes_return_none(raw):
    assert parse_size(raw) is None
