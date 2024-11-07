import requests
import json
from datetime import datetime
from mdparser import regex_parse
from save_to_mongo import save_to_atlas


def main():
    """
    Scrapes book data from a remote Markdown file, parses it, and saves it to both a JSON file and a MongoDB database.

    The function performs the following steps:

    1. Fetches the Markdown content from the specified URL.
    2. Parses the Markdown to extract book information (title, URL, authors, year, category).
    3. Prints statistics about the extracted data (number of books, number of categories).
    4. Saves the parsed book data to a JSON file with a timestamp in the filename.
    5. Saves the parsed book data to a MongoDB Atlas database using the `save_to_atlas` function.

    The Markdown file is expected to follow a specific format for book entries, as documented in the `regex_parse` function.
    """

    md_file_path = "https://raw.githubusercontent.com/yuchdev/CppBooks/refs/heads/master/README.md"
    print("Getting MD file at " + md_file_path)
    markdown_data = requests.get(md_file_path).content.decode('utf-8')

    # Parse Markdown and extract book data
    print("Parsing Markdown to extract book data.")  # Log the process for debugging/monitoring purposes
    books = regex_parse(markdown_data)
    num_books = len(books)  # Count total books
    num_sections = len(set(book["category"] for book in books))  # Count unique sections

    # Print results
    print(f"{num_books} books found in {num_sections} categories.")
    # Save the data as JSON
    timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M")
    filename = f"readmeBooks_{timestamp}.json"

    print("Saving results to", filename)
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(books, file, ensure_ascii=False, indent=4)

    # Save the data to MongoDB Atlas
    print("Saving results to MongoDB Atlas")
    save_to_atlas(books)


if __name__ == "__main__":
    main()
