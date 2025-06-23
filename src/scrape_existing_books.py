import argparse
import asyncio
import csv
import time
import sys
import random

import pandas as pd

from playwright.async_api import async_playwright, Browser  # Import Browser for type hinting

from bookscraper.book_utils import (
    print_log,
    logger,
    check_csv_write_permission
)
from bookscraper.parameters import HEADLESS_BROWSER
from bookscraper.scrape_details import scrape_book
from bookscraper.database import save_books_to_mongodb, get_mongo_collection  # Import new function


def save_books_to_csv(books, filename="books.csv"):
    """
    Saves a list of book dictionaries to a CSV file.

    Args:
        books: A list of dictionaries, where each dictionary represents a book
               and contains key-value pairs for book attributes (e.g., title, author).
        filename: The name of the CSV file to create.
    """
    if not books:
        logger.info(f"No book data to save to {filename}.")
        return

    try:
        # Get all the unique keys (fields) from all dictionaries
        fieldnames = set()
        for book in books:
            # Ensure book is a dictionary before trying to get keys
            if isinstance(book, dict):
                fieldnames.update(book.keys())
        fieldnames = sorted(list(fieldnames))
        logger.info(f"CSV fields for {filename}: {fieldnames}")

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, restval="")
            writer.writeheader()
            for book in books:
                # Double-check before writing, ensuring it's a dictionary
                if isinstance(book, dict):
                    writer.writerow(book)

        print_log(f"Successfully saved {len(books)} books to {filename}", "success")
        logger.info(f"Successfully saved {len(books)} books to {filename}")

    except Exception as e:
        logger.error(f"Error saving books to CSV ({filename}): {e}", exc_info=True)
        print_log(f"Error: Could not write books to CSV file {filename}. Details: {e}", "error")


def save_failed_urls_to_csv(failed_urls_with_status, filename="failed_books.csv"):
    """
    Saves the failed/duplicate URLs with their status to a CSV file.

    Args:
        failed_urls_with_status: A list of tuples, where each tuple is (url, status_string).
        filename: The name of the CSV file to create.
    """
    if not failed_urls_with_status:
        logger.info(f"No failed/duplicate URLs to save to {filename}.")
        return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["url", "status"])  # Add status header
            for url, status in failed_urls_with_status:
                writer.writerow([url, status])
        print_log(f"Successfully saved {len(failed_urls_with_status)} failed/duplicate URLs to {filename}", "success")
        logger.info(f"Successfully saved {len(failed_urls_with_status)} failed/duplicate URLs to {filename}")

    except Exception as e:
        logger.error(f"Error saving failed/duplicate URLs to CSV ({filename}): {e}", exc_info=True)
        print_log(f"Error: Could not write failed/duplicate URLs to CSV file {filename}. Details: {e}", "error")


def save_other_links_to_csv(other_links, filename="other_links.csv"):
    """Saves the 'other' links (skipped URLs) to a CSV file."""
    if not other_links:
        logger.info(f"No 'other' links to save to {filename}.")
        return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["url"])
            for url in other_links:
                writer.writerow([url])
        print_log(f"Successfully saved {len(other_links)} 'other' links to {filename}", "success")
        logger.info(f"Successfully saved {len(other_links)} 'other' links to {filename}")

    except Exception as e:
        logger.error(f"Error saving 'other' links to CSV ({filename}): {e}", exc_info=True)
        print_log(f"Error: Could not write 'other' links to CSV file {filename}. Details: {e}", "error")


def identify_website(url):
    """Identifies the website based on the URL."""
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


async def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Scrape book details from URLs.")
    parser.add_argument("-f", "--input_file", required=True, help="Path to the CSV file containing URLs to scrape.")
    parser.add_argument("-c", "--output_to_csv", action="store_true",
                        help="Output scraped data to CSV files (books.csv, failed_books.csv, other_links.csv).")
    parser.add_argument("-m", "--output_to_mongoDB", action="store_true", help="Output scraped data to a MongoDB Atlas database.")

    args = parser.parse_args()

    # Pre-flight Checks for Output Destinations
    can_output_to_csv = False
    can_output_to_mongo = False

    print_log("\nRunning pre-flight checks for output destinations...", "info")

    # Check CSV write permissions
    print_log("  Checking CSV write permissions...", "info")
    if check_csv_write_permission('.'):
        can_output_to_csv = True
        print_log("  CSV write permission: OK", "info")
    else:
        print_log("  CSV write permission: FAILED. CSV output will not be available.", "error")

    # Initialize MongoDB client and collection
    mongo_client = None
    mongo_collection = None
    # Always attempt MongoDB connection check as part of pre-flight, regardless of -m flag
    print_log("  Checking MongoDB connection...", "info")
    mongo_client, mongo_collection = get_mongo_collection()
    if mongo_client is not None and mongo_collection is not None:
        can_output_to_mongo = True
        print_log("  MongoDB connection: OK", "info")
    else:
        print_log("  MongoDB connection: FAILED. MongoDB output will not be available.", "error")
        # Do NOT set args.mongo = False here; can_output_to_mongo already reflects the failure.

    if not can_output_to_csv and not can_output_to_mongo:
        print_log("\nNo valid output destinations available. Please fix permission/MongoDB issues.", "error")
        sys.exit(1)

    # --- Pre-Scrape Output Confirmation with dynamic choices ---
    # Determine initial output flags based on args and connection checks
    output_to_csv = args.csv and can_output_to_csv
    output_to_mongo = args.mongo and can_output_to_mongo  # This will be true if -m is used AND connection was OK

    # Only prompt if neither -c nor -m flags were passed
    if not args.csv and not args.mongo:  # Changed condition to only prompt if no flags were given
        print_log("No specific output destination chosen via command line arguments (-c, -m).", "info")
        prompt_options = []
        if can_output_to_csv:
            prompt_options.append("(C)SV")
        if can_output_to_mongo:
            prompt_options.append("(M)ongoDB")
        if can_output_to_csv and can_output_to_mongo:
            prompt_options.append("(B)oth")

        prompt_options_str = ", ".join(prompt_options)
        prompt_options_str = prompt_options_str.replace(", (B)oth", " or (B)oth")

        while True:
            if not prompt_options:
                print_log("No output options available. Exiting.", "error")
                sys.exit(1)

            choice = input(f"Do you want to save to {prompt_options_str}, or (E)xit? ").lower().strip()

            if choice == 'c' and can_output_to_csv:
                output_to_csv = True
                break
            elif choice == 'm' and can_output_to_mongo:
                output_to_mongo = True
                break
            elif choice == 'b' and can_output_to_csv and can_output_to_mongo:
                output_to_csv = True
                output_to_mongo = True
                break
            elif choice == 'e':
                print_log("Operation cancelled by user. Exiting.", "info")
                sys.exit(0)
            else:
                print_log("Invalid choice or selected option is not available. Please try again.", "error")

    # If -c or -m was provided, we don't prompt, we just use those settings
    elif args.csv and not can_output_to_csv:
        print_log("CSV output requested but not available due to permission issues. Skipping CSV output.", "warning")
    elif args.mongo and not can_output_to_mongo:
        print_log("MongoDB output requested but not available due to connection issues. Skipping MongoDB output.",
                  "warning")

    # Store URLs to scrape within a dictionary
    website_urls = {
        "amazon": [], "packtpub": [], "leanpub": [], "oreilly": [], "other": []
    }
    # This will store (url, status) tuples for failed or duplicate entries
    failed_urls_with_status = []

    filepath = args.file
    try:
        df = pd.read_csv(filepath, encoding='utf-8')
        for url in df['url']:
            site_identifier = identify_website(url)
            website_urls[site_identifier].append(url)

    except FileNotFoundError:
        logger.critical(f"Error: Input file not found at {filepath}")
        print_log(f"Critical Error: The input file '{filepath}' was not found. Please check the path.", "error")
        sys.exit(1)
    except pd.errors.ParserError:
        logger.critical(f"Error: Could not parse CSV at {filepath}")
        print_log(f"Critical Error: Could not parse the CSV file '{filepath}'. Please check its format.", "error")
        sys.exit(1)
    except KeyError:
        logger.critical(f"Error: CSV file '{filepath}' does not contain a 'url' column.")
        print_log(
            f"Critical Error: The CSV file '{filepath}' does not contain a 'url' column. Please ensure it has a 'url' header.",
            "error")
        sys.exit(1)

    all_urls_to_scrape = []
    batch_size = 10

    for website, urls in website_urls.items():
        if website not in ["other"]:
            print_log(f"Found {len(urls)} {website.capitalize()} URLs to scrape.", "info")
            all_urls_to_scrape.extend(urls)
        else:
            print_log(
                f"Found {len(urls)} {website.capitalize()} URLs which will be skipped and added to other_links.csv.",
                "info")

    total_urls_to_scrape = len(all_urls_to_scrape)

    if total_urls_to_scrape == 0:
        print_log("No valid book URLs found to scrape. Saving skipped links and exiting.", "info")
        save_other_links_to_csv(website_urls["other"])
        sys.exit(0)

    # Playwright Browser Setup and Scraping Loop
    print_log("Starting web scraping operation...", "info")
    async with async_playwright() as p:
        print_log("Opening browser...", "info")
        browser = await p.chromium.launch(headless=HEADLESS_BROWSER)

        books = []  # Stores successfully scraped book details (non-duplicates)

        for i in range(0, total_urls_to_scrape, batch_size):
            batch_urls = all_urls_to_scrape[i:i + batch_size]
            current_batch_num = i // batch_size + 1
            total_batches = (total_urls_to_scrape + batch_size - 1) // batch_size  # Ceiling division
            print_log(f"Starting batch {current_batch_num} of {total_batches}", "info")

            tasks = []
            for url in batch_urls:
                site = identify_website(url)
                # Pass the mongo_collection to scrape_book for immediate duplicate check
                # scrape_book will return a dict on success, or (None, "DUPLICATE"), or (None, "FAILED")
                tasks.append(scrape_book(url, browser, site, mongo_collection))

            results = await asyncio.gather(*tasks)

            for index, result in enumerate(results):
                if isinstance(result, dict):
                    # This is a successfully scraped book (a dictionary)
                    books.append(result)
                elif isinstance(result, tuple) and len(result) == 2 and result[0] is None:
                    # This is a status tuple: (None, "DUPLICATE") or (None, "FAILED")
                    original_url = batch_urls[index]
                    status_type = result[1]  # "DUPLICATE" or "FAILED"

                    # Add to failed_urls_with_status for diagnostic CSV
                    failed_urls_with_status.append((original_url, status_type))

                    if status_type == "DUPLICATE":
                        logger.info(f"Book from URL: {original_url} detected as duplicate and skipped from saving.")
                    elif status_type == "FAILED":
                        logger.error(f"Scraping failed for URL: {original_url}")
                else:
                    # Catch-all for unexpected return types from scrape_book
                    original_url = batch_urls[index]
                    logger.error(f"Unexpected return type from scrape_book for URL: {original_url}. Result: {result}")
                    failed_urls_with_status.append(
                        (original_url, "UNKNOWN_ERROR"))  # Add to failed_urls for diagnostics

            if current_batch_num < total_batches:  # Only pause if there are more batches
                print_log("Pausing between batches...", "info")
                await asyncio.sleep(random.uniform(3, 5))

        total_scraped_books = len(books)  # Only counts successfully scraped books
        total_time_taken = time.time() - start_time
        print_log("Shutting down browser...", "info")
        print_log(
            f"{total_scraped_books} unique books scraped from {total_urls_to_scrape} URLs processed in {total_time_taken:.2f} seconds.",
            "info")
        if total_scraped_books > 0:
            print_log(f"Average time per unique book: {total_time_taken / total_scraped_books:.2f}s", "info")
        else:
            print_log("No unique books were scraped successfully.", "warning")

        await browser.close()

    # Output Saving Based on Resolved Choices and pre-flight checks
    if output_to_csv and can_output_to_csv:
        print_log("Saving scraped books to CSV files...", "info")
        save_books_to_csv(books)  # This now only contains dictionaries
        save_failed_urls_to_csv(failed_urls_with_status)  # This contains URLs and their statuses
        save_other_links_to_csv(website_urls["other"])
    else:
        print_log("CSV output not requested or not available.", "info")
        # If primary CSV output was not chosen or available, still save diagnostic files if possible
        if can_output_to_csv:
            print_log("Saving diagnostic failed/other links to CSV (as primary CSV output for books was not chosen).",
                      "info")
            save_failed_urls_to_csv(failed_urls_with_status)
            save_other_links_to_csv(website_urls["other"])
        else:
            logger.warning("Failed to save diagnostic failed/other links to CSV due to lack of write permissions.")
            print_log("Warning: Failed to save diagnostic failed/other links to CSV due to lack of write permissions.",
                      "warning")

    if output_to_mongo and can_output_to_mongo:
        print_log("Saving scraped books to MongoDB...", "info")
        if books:
            # Pass the mongo_collection to save_books_to_mongodb
            # Use asyncio.to_thread as save_books_to_mongodb might be synchronous
            await asyncio.to_thread(save_books_to_mongodb, books, mongo_collection)
        else:
            print_log("No new unique books scraped to save to MongoDB.", "info")
    else:
        print_log("MongoDB output not requested or not available.", "info")

    # Ensure MongoDB client is closed
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB client closed.")
        print_log("MongoDB client closed.", "info")


if __name__ == "__main__":
    asyncio.run(main())
