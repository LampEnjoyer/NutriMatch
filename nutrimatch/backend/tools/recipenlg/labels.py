"""Allergen and animal-category labels for the ingredients that appear in the imported recipes.
Ingredients missing from this table are emitted as unreviewed with no allergens.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Label:
    allergens: tuple[str, ...]
    animal_category: str
    reviewed: bool


def _group(names: str, allergens: tuple[str, ...] = (), category: str = "none", reviewed: bool = True) -> dict[str, Label]:
    label = Label(allergens, category, reviewed)
    return {name.strip(): label for name in names.split(",") if name.strip()}


LABELS: dict[str, Label] = {}

# Single-ingredient plant foods, spices, oils, sweeteners, drinks and spirits: no major allergen.
LABELS |= _group("""
    salt, onion, sugar, black pepper, water, bell pepper, celery, vanilla extract, lemon, tomato, garlic, brown sugar,
    rice, potato, parsley, vinegar, carrot, mushroom, baking powder, baking soda, green onion, oregano, pineapple,
    mustard, dry mustard, garlic powder, paprika, ketchup, tomato sauce, basil, pea, cornstarch, kidney bean, apple,
    cabbage, broccoli, pimento, olive, olive oil, vegetable oil, shortening, nutmeg, garlic salt, raisin, corn,
    green bean, dill, orange, clove, hot pepper sauce, ginger, bay leaf, tomato paste, cocoa, zucchini, powdered sugar,
    banana, cucumber, corn syrup, celery seed, cider vinegar, lemon zest, spinach, green chile, cornmeal, cumin,
    strawberry, wine vinegar, water chestnut, red onion, peach, yeast, date, allspice, lettuce, cayenne pepper,
    mustard seed, sauerkraut, cauliflower, lentil, caraway seed, cranberry, wine, lima bean, turmeric, cream-style corn,
    sherry, ice, chickpea, orange zest, chive, rosemary, marjoram, celery salt, onion salt, onion powder, pickle relish,
    avocado, asparagus, jalapeno, pinto bean, black bean, pickle, dill pickle, grape, green grape, coriander,
    brown rice, wild rice, cayenne, red wine, white wine, popcorn, pumpkin, poppy seed, apricot, okra, apple cider,
    salsa, picante sauce, active yeast, mandarin orange, sage, cherry, applesauce, red potato, coffee, candied cherry,
    candied pineapple, pear, summer squash, red pepper flakes, chili pepper, navy bean, blueberry, eggplant,
    lemonade, turnip, ginger ale, rhubarb, yam, cranberry juice, apricot nectar, cranberry sauce, green tomato,
    cream of tartar, peppercorn, lime, prune, monosodium glutamate, mint, radish, caper, shallot, brandy,
    maraschino cherry, lemon extract, bourbon, rum, balsamic vinegar, maple syrup, cantaloupe, tarragon vinegar,
    tarragon, thyme, tea, apricot preserves, marmalade, snow pea, tapioca, artichoke heart, cherry tomato,
    liquid smoke, tomato puree, new potato, club soda, sugar substitute, mace, butter bean, red food coloring,
    grapefruit, raspberry, currant, fruit cocktail, bean sprout, horseradish, dijon mustard, chili sauce,
    molasses, coconut, corn tortilla, cardamom, fig, cinnamon, artificial sweetener, beet, black-eyed pea,
    brussels sprout, great northern bean, grits, kiwi, leek, mandarin, orange extract, orange juice, peas and carrots,
    sunflower seed, unpeeled apple, tomatoes green chily
""")

# Dairy: always contains milk.
LABELS |= _group(
    """butter, milk, cheddar cheese, sour cream, cheese, parmesan cheese, cream cheese, heavy cream, evaporated milk,
    buttermilk, mozzarella cheese, american cheese, cream, cottage cheese, yogurt, processed cheese, swiss cheese,
    half and half, monterey jack cheese, condensed milk, powdered milk, provolone cheese, ricotta cheese""",
    ("milk",), "dairy",
)

LABELS |= _group("egg, egg yolk, egg white, mayonnaise", ("egg",), "egg")
LABELS |= _group("egg noodle", ("egg", "wheat", "gluten"), "egg")
LABELS |= _group("tuna, salmon, fish fillet", ("fish",), "fish")
LABELS |= _group("shrimp, crabmeat, clam, scallop, oyster", ("shellfish",), "shellfish")
LABELS |= _group("peanut, roasted peanut, peanut butter, peanut oil", ("peanut",))
LABELS |= _group("pecan, almond, walnut, cashew, macadamia nut, almond extract", ("tree_nut",))
LABELS |= _group("sesame seed, sesame oil", ("sesame",))
LABELS |= _group("all-purpose flour, self-rising flour, cake flour, wheat flour, wheat germ", ("wheat", "gluten"))
LABELS |= _group("barley, beer", ("gluten",))
LABELS |= _group("soy sauce", ("soy", "wheat", "gluten"))
LABELS |= _group("blue cheese", ("milk",), "dairy")
LABELS |= _group("unbleached flour", ("wheat", "gluten"))
LABELS |= _group("honey", (), "honey")
LABELS |= _group("macaroni, shell macaroni, spaghetti, linguine, fettuccine, lasagna noodle, pasta", ("wheat", "gluten"))

# Whole cuts and fats from one animal.
LABELS |= _group(
    "beef, ground beef, beef round, beef chuck, flank steak, corned beef, pork, pork chop, pork ribs, ham, bacon, "
    "veal, salt pork, lard, bacon grease, pork tenderloin",
    (), "meat",
)
LABELS |= _group("chicken, chicken breast, chicken wing, turkey", (), "poultry")
# Gelatin is animal-derived, so it matters for vegetarian filtering even though it is not an allergen.
LABELS |= _group("gelatin, jello, marshmallow", (), "meat")

# Everything below is blended, branded or varies by product: likely allergens listed, but not known complete.
LABELS |= _group("sausage, italian sausage, pepperoni, hot dog", (), "meat", reviewed=False)
LABELS |= _group("chicken broth", (), "poultry", reviewed=False)
LABELS |= _group("beef broth", (), "meat", reviewed=False)
LABELS |= _group("cream of mushroom soup, cream of celery soup, cheddar cheese soup", ("milk", "wheat", "gluten"), "dairy", False)
LABELS |= _group("cream of potato soup", ("milk", "wheat", "gluten"), "dairy", False)
LABELS |= _group("angel food cake", ("wheat", "gluten", "egg"), "egg", False)
LABELS |= _group("cream of chicken soup", ("milk", "wheat", "gluten"), "poultry", False)
LABELS |= _group("tomato soup", ("milk", "wheat", "gluten"), "none", False)
LABELS |= _group("onion soup mix", ("wheat", "soy", "gluten"), "none", False)
LABELS |= _group("worcestershire, worcestershire sauce", ("fish",), "fish", False)
LABELS |= _group("barbecue sauce, spaghetti sauce, italian dressing, taco seasoning, italian seasoning, "
                 "poultry seasoning, seasoned salt, lemon pepper, curry powder, chili powder, pickling spice, "
                 "vegetable, enchilada sauce, taco sauce, french dressing, pumpkin pie spice, pork and beans, baked beans, refried bean, margarine, potato chip, tortilla chip, "
                 "corn chip, pie filling, chocolate syrup", (), "none", False)
LABELS |= _group("salad dressing", ("egg",), "none", False)
LABELS |= _group("egg substitute", ("egg",), "egg", False)
LABELS |= _group("whipped topping, ice cream, instant pudding, vanilla pudding, vanilla pudding mix, caramel, orange sherbet, "
                 "raspberry sherbet", ("milk",), "dairy", False)
LABELS |= _group("butter bud", (), "dairy", False)
LABELS |= _group("chocolate chip, chocolate", ("milk", "soy"), "none", False)
LABELS |= _group("semi-sweet chocolate", ("soy",), "none", False)
LABELS |= _group("butterscotch chip", ("milk", "soy"), "dairy", False)
LABELS |= _group("peanut butter chip", ("peanut", "milk", "soy"), "dairy", False)
LABELS |= _group("marshmallow creme", ("egg",), "none", False)
LABELS |= _group("oat, oat bran, quaker oat", (), "none", False)
LABELS |= _group("cornflake, crisp rice cereal", ("gluten",), "none", False)
LABELS |= _group("bran flakes", ("wheat", "gluten"), "none", False)
LABELS |= _group("noodle", ("wheat", "gluten"), "none", False)
LABELS |= _group(
    "bread, french bread, english muffin, bun, flour tortilla, biscuit, cracker, cracker crumb, graham cracker, "
    "bread crumb, crouton, pretzel, stuffing mix, vanilla wafer, chow mein noodle",
    ("wheat", "gluten"), "none", False,
)
LABELS |= _group("crescent roll, pie crust, baked pie shell, biscuit mix, muffin mix, cake mix", ("wheat", "gluten", "milk"), "none", False)
LABELS |= _group("french fried onion", ("wheat", "gluten"), "none", False)


def label_for(normalized_name: str) -> Label | None:
    return LABELS.get(normalized_name)
