import argparse
import csv
import time
from src.bookscraper import scrape_details
import pandas as pd
from playwright.sync_api import sync_playwright


def save_books_to_csv(books, filename="books.csv"):
    """Saves a list of book dictionaries to a CSV file."""

    if not books:
        print("No book data to save.")
        return

    try:
        # Get all the unique keys (fields) from all dictionaries
        fieldnames = set()
        for book in books:
            if book:  # Check if the book dictionary is not None
                fieldnames.update(book.keys())
        fieldnames = sorted(list(fieldnames))  # Convert to a sorted list for consistent order

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, restval="")  # restval for missing data
            writer.writeheader()
            for book in books:
                if book is not None:
                    writer.writerow(book)  # Write each book's data

        print(f"Books saved to {filename}")

    except Exception as e:
        print(f"Error saving books to CSV: {e}")


def main():
    parser = argparse.ArgumentParser(description="Scrape book details from URLs.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="Path to the CSV file containing URLs.")
    args = parser.parse_args()

    amazon_urls = []  # Initialize an empty list for Amazon books
    packtpub_urls = []  # Initialize an empty list for Packtpub books
    leanpub_urls = []  # Initialize an empty list for Leanpub books
    oreilly_urls = []  # Initialize an empty list for O'Reilly books
    other_urls = []  # Initialize an empty list for other books (PDFs, portals, etc.)

    if args.file:
        filepath = args.file
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
            for url in df['url']:
                if "amazon.com" in url:  # Filter for Amazon URLs
                    amazon_urls.append(url)
                elif "packtpub.com" in url:  # Filter for Packtpub URLs
                    packtpub_urls.append(url)

                elif "leanpub.com" in url:  # Filter for Leanpub URLs
                    leanpub_urls.append(url)

                elif "oreilly.com" in url:  # Filter for O'Reilly URLs
                    oreilly_urls.append(url)

                else:
                    other_urls.append(url)

        except FileNotFoundError:
            print(f"Error: File not found at {filepath}")
            return
        except pd.errors.ParserError:
            print(f"Error: Could not parse CSV at {filepath}")
            return

    print(f" {len(amazon_urls)} Amazon URLs to scrape.")
    print(f" {len(packtpub_urls)} PacktPub URLs to scrape.")
    print(f" {len(leanpub_urls)} LeanPub URLs to scrape.")
    print(f" {len(oreilly_urls)} O'Reilly URLs to scrape.")
    print(f" {len(other_urls)} Other URLs in file.")

    # print(amazon_urls)
    books = []

    start = time.time()

    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=scrape_details.get_random_user_agent())
        page = context.new_page()

        print("Fetching Amazon book details...")
        for url in amazon_urls:
            time.sleep(1)
            books.append(scrape_details.scrape_amazon(url, page))

        print("Fetching PactPub book details...")
        for url in packtpub_urls:
            time.sleep(1)
            books.append(scrape_details.scrape_packtpub(url, page))

        print("Fetching LeanPub book details...")
        for url in leanpub_urls:
            time.sleep(1)
            books.append(scrape_details.scrape_leanpub(url, page))

        print("Fetching O'Reilly book details...")
        for url in oreilly_urls:
            time.sleep(1)
            books.append(scrape_details.scrape_oreilly(url, page))

        print("Shutting down browser")
        browser.close()

        end = time.time()

        # print(books)
        print(f"Time spent: {end - start} seconds")

        save_books_to_csv(books)


if __name__ == "__main__":
    main()
