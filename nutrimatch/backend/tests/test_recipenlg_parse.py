import pytest

from tools.recipenlg.parse import parse_ingredient, parse_recipe


@pytest.mark.parametrize(
    ("line", "name", "quantity", "unit"),
    [
        ("1 1/2 c. firmly packed brown sugar", "brown sugar", 1.5, "cup"),
        ("2 Tbsp. butter or margarine", "butter", 2, "tbsp"),
        ("1/2 tsp. vanilla flavoring", "vanilla extract", 0.5, "tsp"),
        ("1 (8 oz.) pkg. cream cheese, softened", "cream cheese", 8, "oz"),
        ("2 (6 1/2 oz.) cans minced clams", "clam", 13, "oz"),
        ("1 stick oleo", "margarine", 4, "oz"),
        ("4 boned chicken breasts", "chicken breast", 4, "piece"),
        ("3 stalks celery", "celery", 3, "piece"),
        ("1 lb. hamburger", "ground beef", 1, "lb"),
        ("2 cloves garlic, minced", "garlic", 2, "clove"),
    ],
)
def test_parses_quantity_unit_and_canonical_name(line, name, quantity, unit):
    parsed = parse_ingredient(line)
    assert parsed["name"] == name
    assert parsed["quantity"] == pytest.approx(quantity)
    assert parsed["unit"] == unit


def test_container_without_a_size_is_not_convertible():
    parsed = parse_ingredient("1 can cream of mushroom soup")
    assert parsed["name"] == "cream of mushroom soup"
    assert parsed["unit"] is None
    assert parsed["convertible"] is False


def test_line_without_a_quantity_is_unmeasured():
    parsed = parse_ingredient("salt and pepper")
    assert parsed["quantity"] is None
    assert parsed["measured"] is False


def test_alternate_spellings_map_to_one_name():
    names = {parse_ingredient(f"1 c. {raw}")["name"] for raw in ("confectioners sugar", "powdered sugar", "icing sugar")}
    assert names == {"powdered sugar"}


def test_parse_recipe_extracts_steps_and_servings():
    text = (
        "Chicken Delight\n\nIngredients:\n- 4 chicken breasts\n- 1 c. milk\n\n"
        "Directions:\n- Mix milk in a baking dish.\n- Bake at 350 for 1 hour.\n- Serves 4."
    )
    recipe = parse_recipe(text)
    assert recipe["title"] == "Chicken Delight"
    assert recipe["ingredient_lines"] == ["4 chicken breasts", "1 c. milk"]
    assert len(recipe["steps"]) == 3
    assert recipe["servings"] == 4


def test_parse_recipe_without_a_servings_line_has_none():
    text = "Toast\n\nIngredients:\n- 2 slices bread\n\nDirections:\n- Toast the bread."
    assert parse_recipe(text)["servings"] is None


def test_parse_recipe_rejects_text_without_the_expected_sections():
    assert parse_recipe("Just a title and some words") is None
