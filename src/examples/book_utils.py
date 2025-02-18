import hashlib


def hash_book(title: str = "", authors: list = [None], year=None) -> str:
    """Calculates a SHA-256 hash for a book based on its title, authors, and year.

    Args:
        title: The title of the book (required).
        authors: The authors of the book, separated by commas (required).
        year: The publication year of the book (optional, default is 0).

    Returns:
        A hexadecimal string representing the SHA-256 hash of the combined fields.
    """

    if authors is None:
        authors = []
    try:
        # Validate input
        if not title:
            raise ValueError("Title is required.")
        if not authors:
            authors = None

        year = str(year)  # Ensure year is a string for hashing

        combined_fields = f"{title}|{authors}|{year}"
        hash_object = hashlib.sha256()
        hash_object.update(combined_fields.encode('utf-8'))
        return hash_object.hexdigest()
    except (TypeError, ValueError) as e:
        print(f"Error hashing book: {e}")
        return ''
