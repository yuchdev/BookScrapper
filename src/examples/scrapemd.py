import requests
from datetime import datetime
from mdparser import regex_parse
from save_to_mongo import save_to_atlas
import pandas as pd


def main():
    """
    Scrapes book data from a remote Markdown file, parses it, and saves it to both a JSON file and a MongoDB database.

    The function performs the following steps:

    1. Fetches the Markdown content from the specified URL.
    2. Parses the Markdown to extract book information (title, URL, authors, year, category).
    3. Prints statistics about the extracted data (number of books, number of categories).
    4. Saves the parsed book data to a JSON file with a timestamp in the filename.
    5. Saves the parsed book data to a MongoDB Atlas database using the `save_to_atlas` function.

    The Markdown file is expected to follow a specific format for book entries, as documented in the `regex_parse`
     function.
    """

    def json_to_csv_pandas(json_data, csv_filename):
        """Converts JSON data to CSV using Pandas.  Handles nested JSON well.

        Args:
            json_data: The JSON data (can be a list or a dictionary, even nested).
            csv_filename: The name of the CSV file.
        """
        try:
            df = pd.json_normalize(json_data)  # Use json_normalize for nested JSON
            df.to_csv(csv_filename, index=False, encoding='utf-8')
            print(f"JSON data successfully saved to {csv_filename}")
        except Exception as e:
            print(f"An error occurred: {e}")

    STORAGE = "local"

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
    # filename = f"readmeBooks_{timestamp}.json"
    filename = f"readmeBooks_{timestamp}.csv"

    match STORAGE:
        case "local":
            print("Saving results to", filename)
            # with open(filename, "w", encoding="utf-8") as file:
            #     json.dump(books, file, ensure_ascii=False, indent=4)
            # with open(filename, "w", newline="") as csvfile:
            #     writer = csv.writer(csvfile)
            #     writer.writerows(books)  # Write all rows at once
            json_to_csv_pandas(books, "output_from_file_pandas.csv")

        case "remote":
            # Save the data to MongoDB Atlas
            print("Saving results to MongoDB Atlas")
            save_to_atlas(books)


if __name__ == "__main__":
    main()
