"""Parse RecipeNLG-style recipe text into structured recipes. Pure functions, no I/O."""

import re

from tools.recipenlg.aliases import ALIASES

FRACTIONS = {"¼": "1/4", "½": "1/2", "¾": "3/4", "⅓": "1/3", "⅔": "2/3", "⅛": "1/8"}

# source unit token -> (nutrimatch unit, multiplier into that unit); None unit means "needs a size".
UNIT_MAP = {
    "c": ("cup", 1), "cup": ("cup", 1), "cups": ("cup", 1),
    "tbsp": ("tbsp", 1), "tablespoon": ("tbsp", 1), "tablespoons": ("tbsp", 1), "tbs": ("tbsp", 1), "T": ("tbsp", 1),
    "tsp": ("tsp", 1), "teaspoon": ("tsp", 1), "teaspoons": ("tsp", 1), "t": ("tsp", 1),
    "oz": ("oz", 1), "ounce": ("oz", 1), "ounces": ("oz", 1),
    "lb": ("lb", 1), "lbs": ("lb", 1), "pound": ("lb", 1), "pounds": ("lb", 1),
    "pt": ("cup", 2), "pint": ("cup", 2), "pints": ("cup", 2),
    "qt": ("cup", 4), "quart": ("cup", 4), "quarts": ("cup", 4),
    "gal": ("cup", 16), "gallon": ("cup", 16),
    "g": ("g", 1), "gram": ("g", 1), "grams": ("g", 1), "kg": ("kg", 1),
    "ml": ("ml", 1), "l": ("l", 1),
    "clove": ("clove", 1), "cloves": ("clove", 1),
    "slice": ("slice", 1), "slices": ("slice", 1),
    "pinch": ("pinch", 1), "dash": ("pinch", 1),
}
# Containers: only convertible when the line gives a size in parentheses, e.g. "1 (4 oz.) can".
CONTAINERS = {"can", "cans", "pkg", "pkgs", "package", "packages", "jar", "jars", "carton", "cartons",
              "box", "boxes", "bottle", "bottles", "envelope", "envelopes", "bag", "bags", "container", "containers"}
SIZE_WORDS = {"large", "lg", "small", "sm", "medium", "med", "heaping", "scant", "generous", "level", "rounded"}
DESCRIPTORS = {"fresh", "freshly", "finely", "chopped", "diced", "minced", "sliced", "grated", "shredded", "ground",
               "crushed", "peeled", "softened", "melted", "cooked", "uncooked", "raw", "frozen", "canned", "dried",
               "packed", "firmly", "boneless", "skinless", "lean", "extra", "virgin", "whole", "plain", "good",
               "quality", "unsalted", "salted", "sweetened", "unsweetened", "light", "low", "fat", "reduced",
               "cut", "up", "optional", "or", "and", "the", "a", "an", "about", "approximately", "chunk", "chunks",
               "can", "cans", "pkg", "pkgs", "head", "heads", "stalk", "stalks", "rib", "ribs", "bunch", "bunches",
               "thinly", "coarsely", "sifted", "unsifted", "sq", "drops", "drop", "sticks", "stick", "strips", "strip",
               "ears", "doz", "each", "ripe", "soft", "beaten", "slightly", "well", "scalded", "warm", "cold", "chilled",
               "toasted", "mashed", "cubed", "drained", "halve", "piece", "pieces", "slice", "slices", "mini", "miniature",
               "tiny", "snipped", "broken", "pitted", "seedless", "commercial", "regular", "instant", "stuffed", "buttered",
               "hard-boiled", "hard-cooked", "boiled", "liquid", "bulk", "mild", "sharp", "creamy", "chunky", "crunchy",
               "thin", "wide", "fine", "dry", "tart", "yellow", "purple", "sweet", "size", "with", "top", "in", "juice",
               "pure", "real", "diet", "calorie", "cooking", "flaked", "blanched", "slivered", "rubbed", "mixed",
               "refrigerated", "prepared", "condensed", "skim", "nonfat", "dark", "white",
               "pared", "shelled", "diagonally", "stiffly", "crisply", "squeezed", "skinned", "boned", "deveined",
               "unbeaten", "well-beaten", "tub", "jar", "bottle", "scoops", "dashes", "sprigs"}


def to_number(text: str) -> float | None:
    text = text.strip()
    for ch, rep in FRACTIONS.items():
        text = text.replace(ch, " " + rep)
    text = text.strip()
    if not text:
        return None
    total = 0.0
    for part in text.split():
        if "/" in part:
            num, _, den = part.partition("/")
            try:
                total += float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                return None
        else:
            try:
                total += float(part)
            except ValueError:
                return None
    return total if total > 0 else None


QTY_RE = re.compile(r"^(?P<q>\d+(?:\s+\d+/\d+|/\d+|\.\d+)?)(?:\s*(?:-|to)\s*\d+(?:\s+\d+/\d+|/\d+|\.\d+)?)?\s*(?P<rest>.*)$")
SIZE_RE = re.compile(r"^\(\s*(?P<n>\d+(?:\.\d+|\s+\d+/\d+|/\d+)?)\s*(?:-\s*)?(?P<u>[a-zA-Z.]+)\s*\.?\s*\)\s*(?P<rest>.*)$")


def clean_name(text: str) -> str:
    text = text.lower().split(",")[0]
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.split(r" - | for | or |/| plus |;| such as | like ", text)[0]
    words = [w.strip(".:-*") for w in text.split()]
    phrase = " ".join(w for w in words if w)
    if phrase in ALIASES:
        return ALIASES[phrase]
    words = [w for w in words if w and w not in SIZE_WORDS and w not in DESCRIPTORS]
    name = " ".join(words)
    if name in ALIASES:
        return ALIASES[name]
    # light singularisation: tomatoes->tomato, berries->berry, otherwise strip a trailing s
    if name.endswith("ies") and len(name) > 4:
        name = name[:-3] + "y"
    elif name.endswith("oes"):
        name = name[:-2]
    elif name.endswith(("ches", "shes", "sses", "xes")):
        name = name[:-2]
    elif name.endswith("s") and not name.endswith(("ss", "us")) and len(name) > 3:
        name = name[:-1]
    return ALIASES.get(name, name)


def parse_ingredient(line: str) -> dict:
    """Return {name, quantity, unit, notes, measured, convertible} for one ingredient line."""
    raw = line.strip().lstrip("-").strip()
    notes = raw.partition(",")[2].strip() or None
    m = QTY_RE.match(raw)
    if not m:
        return {"raw": raw, "name": clean_name(raw), "quantity": None, "unit": None, "notes": notes,
                "measured": False, "convertible": False}
    qty = to_number(m.group("q"))
    rest = m.group("rest").strip()
    size = SIZE_RE.match(rest)
    size_amount = None
    if size:
        n, u = to_number(size.group("n")), size.group("u").strip(".").lower()
        if n and u in UNIT_MAP:
            unit, mult = UNIT_MAP[u]
            size_amount = (n * mult, unit)
        rest = size.group("rest").strip()
    parts = rest.split(None, 1)
    token = parts[0].strip(".").rstrip(",") if parts else ""
    after = parts[1] if len(parts) > 1 else ""
    token_key = token if token in ("T", "t") else token.lower()
    if token_key in UNIT_MAP and qty:
        unit, mult = UNIT_MAP[token_key]
        after = re.sub(r"^of\s+", "", after)
        return {"raw": raw, "name": clean_name(after), "quantity": qty * mult, "unit": unit, "notes": notes,
                "measured": True, "convertible": True}
    if token_key in CONTAINERS and qty:
        after = re.sub(r"^of\s+", "", after)
        if size_amount:
            return {"raw": raw, "name": clean_name(after), "quantity": qty * size_amount[0], "unit": size_amount[1],
                    "notes": notes, "measured": True, "convertible": True}
        return {"raw": raw, "name": clean_name(after), "quantity": qty, "unit": None, "notes": notes,
                "measured": True, "convertible": False}
    if token_key == "stick" and qty:
        return {"raw": raw, "name": clean_name(after), "quantity": qty * 4, "unit": "oz", "notes": notes,
                "measured": True, "convertible": True}
    # "4 chicken breasts", "1 large onion": a count of the thing itself.
    return {"raw": raw, "name": clean_name(rest), "quantity": qty, "unit": "piece", "notes": notes,
            "measured": True, "convertible": True}


SERVES_RE = re.compile(r"\b(?:serves|servings?|makes|yields?)[:\s]+(?:about\s+|approximately\s+)?(\d{1,2})(?:\s*(?:-|to)\s*(\d{1,2}))?\b", re.I)


def parse_recipe(text: str) -> dict | None:
    head, sep, rest = text.partition("\n\nIngredients:\n")
    if not sep:
        return None
    ing_block, sep2, dir_block = rest.partition("\n\nDirections:\n")
    if not sep2:
        return None
    ing_lines = [l[2:].strip() for l in ing_block.split("\n") if l.startswith("- ") and l[2:].strip()]
    steps = [l[2:].strip() for l in dir_block.split("\n") if l.startswith("- ") and l[2:].strip()]
    servings = None
    for step in reversed(steps):
        m = SERVES_RE.search(step)
        if m:
            servings = int(m.group(2) or m.group(1))
            break
    return {"title": head.strip(), "ingredient_lines": ing_lines, "steps": steps, "servings": servings}
