import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from bookscraper.scrape_details import scrape_amazon


def load_json_file(file_path):
    """
    Loads data from a JSON file.

    Args:
      file_path: Path to the JSON file.

    Returns:
      The loaded JSON data as a Python object (usually a dictionary).
      Returns None if the file cannot be loaded.
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return None

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None


def main():
    file_path = 'readmeBooks_2024-12-19_08.42.json'
    data = load_json_file(file_path)
    amazon = []

    # Check if the data is a list (array)
    for entry in data:
        if 'amazon' in entry['site']:
            amazon.append(entry)
    print(amazon)

        # scrape_amazon("https://www.amazon.com/dp/0201717069")


if __name__ == "__main__":
    main()
