import argparse
import asyncio
import csv
import time
import urllib.parse

import pandas as pd

from playwright.async_api import async_playwright, TimeoutError
import random

from src.bookscraper.book_utils import print_log
from src.bookscraper.scrape_details import scrape_book


def save_books_to_csv(books, filename="books.csv"):
    """
    Saves a list of book dictionaries to a CSV file.

    Args:
        books: A list of dictionaries, where each dictionary represents a book
               and contains key-value pairs for book attributes (e.g., title, author).
        filename: The name of the CSV file to create.
    """
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


def save_failed_urls_to_csv(failed_urls, filename="failed_books.csv"):
    """Saves the failed URLs to a CSV file."""
    if not failed_urls:
        print("No failed URLs to save.")
        return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["url"])  # Write header
            for url in failed_urls:
                writer.writerow([url])

        print(f"Failed URLs saved to {filename}")

    except Exception as e:
        print(f"Error saving failed URLs to CSV: {e}")


def save_other_links_to_csv(other_links, filename="other_links.csv"):
    """Saves the 'other' links to a CSV file."""
    if not other_links:
        print("No 'other' links to save.")
        return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["url"])
            for url in other_links:
                writer.writerow([url])

        print(f"'Other' links saved to {filename}")

    except Exception as e:
        print(f"Error saving 'other' links to CSV: {e}")


async def main():
    """
    Asynchronously scrape book details from URLs provided in a CSV file.

    This function sets up command-line argument parsing, reads URLs from a CSV file,
    categorizes them by website, and then scrapes Amazon book details in batches.
    It uses Playwright for web scraping and implements concurrent scraping with
    asyncio for improved performance.

    Command-line Arguments:
        -f, --file: Path to the CSV file containing URLs (required).

    The function performs the following steps:
    1. Parse command-line arguments.
    2. Read and categorize URLs from the specified CSV file.
    3. Initialize a Playwright browser.
    4. Scrape Amazon book details in batches.
    5. Save the scraped book details to a CSV file.

    Returns:
        None. The function saves the scraped data to a CSV file as a side effect.

    Raises:
        FileNotFoundError: If the specified CSV file is not found.
        pd.errors.ParserError: If there's an error parsing the CSV file.
    """
    parser = argparse.ArgumentParser(description="Scrape book details from URLs.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="Path to the CSV file containing URLs.")
    args = parser.parse_args()

    # Store URLs to scrape within a dictionary
    website_urls = {
        "amazon": [],
        "packtpub": [],
        "leanpub": [],
        "oreilly": [],
        "other": []
    }
    failed_urls = []  # Initialize an empty list for failed books

    if args.file:
        filepath = args.file
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
            for url in df['url']:
                if "amazon.com" in url:
                    website_urls["amazon"].append(url)
                elif "packtpub.com" in url:
                    website_urls["packtpub"].append(url)
                elif "leanpub.com" in url:
                    website_urls["leanpub"].append(url)
                elif "oreilly.com" in url:
                    website_urls["oreilly"].append(url)
                else:
                    website_urls["other"].append(url)

        except FileNotFoundError:
            print(f"Error: File not found at {filepath}")
            return
        except pd.errors.ParserError:
            print(f"Error: Could not parse CSV at {filepath}")
            return

    # all_urls = website_urls["oreilly"]  # For single-site testing
    all_urls = []
    batch_size = 10
    for website, urls in website_urls.items():
        if website not in ["other"]:
            print_log(f" {len(urls)} {website.capitalize()} URLs to scrape.", "info")
            all_urls.extend(urls)
        else:
            print_log(f" {len(urls)} {website.capitalize()} URLs will be skipped and added to other_links.csv.", "info")
    total_urls = len(all_urls)

    async with async_playwright() as p:
        print("Opening browser")
        browser = await p.chromium.launch(headless=True)

        books = []
        start = time.time()

        for i in range(0, total_urls, batch_size):
            batch_urls = all_urls[i:i + batch_size]
            print(f"Starting batch {i // batch_size + 1}")

            tasks = []
            for url in batch_urls:
                site = identify_website(url)
                tasks.append(scrape_book(url, browser, site))  # pass the site identifier.

            results = await asyncio.gather(*tasks)

            for index, result in enumerate(results):
                if result:
                    books.append(result)
                else:
                    failed_urls.append(batch_urls[index])
                    print(f"Failed urls: {failed_urls}")

            if i + batch_size < total_urls:
                print("Pausing between batches...")
                await asyncio.sleep(random.uniform(3, 5))

        print("Shutting down browser...")
        total_time = time.time() - start
        print(
            f"{total_urls} books checked and scraped in {total_time} seconds at a rate of {total_time / total_urls}s per book")

        await browser.close()

    save_books_to_csv(books)
    save_failed_urls_to_csv(failed_urls)
    save_other_links_to_csv(website_urls["other"])


def identify_website(url):
    if "amazon.com" in url:
        return "amazon"
    elif "packtpub.com" in url:
        return "packtpub"
    elif "leanpub.com" in url:
        return "leanpub"
    elif "oreilly.com" in url:
        return "oreilly"
    else:
        return "other"


if __name__ == "__main__":
    asyncio.run(main())
