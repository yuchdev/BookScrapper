import hashlib
from datetime import datetime


def print_log(text, status: str):
    """Prints the given text in red to stdout."""
    match status:
        case "error":
            color = "\033[31m"  # ANSI escape code for red text
        case "info":
            color = "\033[33m"  # ANSI escape code for yellow text
        case _:
            color = "\033[0m"  # ANSI escape code to reset text color
    reset_color_code = "\033[0m"  # ANSI escape code to reset text color

    print(f"{color}{text}{reset_color_code}")


def extract_year_from_date(date_string: str) -> int | None:
    """
    Extracts the year from a date string.

    Args:
      date_string: The date string in any supported format (e.g., "2023-12-19", "December 17, 2019", "1995").

    Returns:
      int: The extracted year, or None if the year cannot be extracted.
    """
    try:
        # Attempt to parse the date string using different formats
        for date_format in ["%Y-%m-%d", "%B %d, %Y", "%Y"]:
            try:
                date_object = datetime.strptime(date_string, date_format)
                return date_object.year
            except ValueError:
                continue  # Try the next format

    except Exception as e:
        print(f"Error extracting year: {e}")
        return None


def hash_book(title: str = "", authors: list = [None], year=None) -> str:
    """
    Calculates a SHA-256 hash for a book based on its title, authors, and year.

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
