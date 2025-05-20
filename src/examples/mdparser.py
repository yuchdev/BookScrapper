import re
from book_utils import hash_book
import validators
import csv


def regex_parse(markdown_data: str) -> list[dict]:
    """
    Parses book information from a markdown string.

    Extracts book titles, URLs, authors (if available), and publication years (if available)
    from the provided markdown data.

    Args:
        markdown_data (str): The markdown content as a string.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a parsed book
            with the following keys:
                "category" (str): The category section from the markdown (e.g., "C++ Primer Books").
                "title" (str): The title of the book.
                "url" (str): The URL of the book (extracted from the markdown).
                "author" (str or None): The author(s) of the book (extracted from the markdown).
                "year" (str or None): The publication year of the book (extracted from the markdown).
    """
    books = []
    current_section = None
    year = None

    for line in markdown_data.splitlines():
        line.strip()
        if line.startswith('## '):
            current_section = line.strip("#").strip()

        elif line.startswith("* "):
            title = re.search(r"\[(.*?)]", line).group(1)
            url_author_year = re.findall(r"\((.?|.+?)\)", line)
            url = None

            for i in url_author_year:
                if "http" in i:
                    url = i
                    break

            # Validate the URL using the validators library
            try:
                if not validators.url(url):
                    print("Invalid URL:", url)
                    raise ValueError(f"Invalid URL: {url}")
            except ValueError as e:
                print(f"Error parsing book entry: {e} for {title}")
                # Optionally: Skip this entry and continue processing others
                continue

            site_pattern = r"(?://(.+?)/)"
            try:
                match = re.findall(site_pattern, url)
                if match:
                    site = match[0]
                else:
                    site = ''
            except Exception as e:
                site = ''
                print(f"Error occurred while parsing URL: {e}")

            if len(url_author_year) > 1:
                author_year = url_author_year[1]

                # Split authors by comma and strip whitespace
                author_pattern = r"^[\D]+$"

                match = re.match(r"^(.*?)(?:,\s*(\d{4}))?$", author_year)
                if match:
                    if re.match(r"^\d+$", match.group(1)):  # Only a year
                        authors = [None]
                        year = int(match.group(1))
                    else:
                        authors = [author.strip() for author in match.group(1).split(",") if
                                   re.match(author_pattern, author)]
                        year = match.group(2)

                else:
                    authors = [url_author_year]
            else:
                authors, year = [None], None
            if year:
                year = int(year)

            book_hash = hash_book(title, authors, year)

            books.append({
                "title": title,
                "hash": book_hash,
                "isbn": None,
                "authors": authors,
                "publication_year": year,
                "category": current_section,
                "url": url,
                "description": None,
                "tags": [None],
                "site": site,
            })

    return books
