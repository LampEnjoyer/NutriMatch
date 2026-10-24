def normalize_name(raw: str) -> str:
    """Lowercase, trim and collapse internal whitespace. Used for ingredient keys and search terms."""
    words = raw.strip().lower().split()
    return " ".join(words)
