import unicodedata


def strip_accents(text: str) -> str:
    """Remove accents from a string, returning only ASCII characters."""

    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces and trim leading/trailing spaces."""

    return " ".join(part for part in text.split() if part)


def normalize_municipality_name(raw_name: str) -> str:
    """Normalize municipality names for matching.

    Steps:
    - lower-case
    - remove accents
    - replace hyphens by spaces
    - normalize whitespace
    """

    text = raw_name.strip().lower()
    text = text.replace("-", " ")
    text = strip_accents(text)
    text = normalize_whitespace(text)
    return text


def levenshtein_distance(a: str, b: str) -> int:
    """Compute a simple Levenshtein distance between two strings.

    Implemented here to keep the domain free from external dependencies.
    """

    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    # Classic dynamic programming implementation
    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current_row = [i]
        for j, cb in enumerate(b, start=1):
            insert_cost = current_row[j - 1] + 1
            delete_cost = prev_row[j] + 1
            replace_cost = prev_row[j - 1] + (0 if ca == cb else 1)
            current_row.append(min(insert_cost, delete_cost, replace_cost))
        prev_row = current_row
    return prev_row[-1]
