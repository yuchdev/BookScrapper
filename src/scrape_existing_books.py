import argparse
import asyncio
import csv
import time
import sys
import os

import pandas as pd

from playwright.async_api import async_playwright
import random

from bookscraper.book_utils import (
    print_log,
    logger,
    check_csv_write_permission,
    check_mongodb_connection,
    get_default_urls_file,
    create_default_urls_file)
from bookscraper.scrape_details import scrape_book
from bookscraper.database import save_books_to_mongodb


def save_books_to_csv(books, filename="books.csv"):
    """
    Saves a list of book dictionaries to a CSV file.

    Args:
        books: A list of dictionaries, where each dictionary represents a book
               and contains key-value pairs for book attributes (e.g., title, author).
        filename: The name of the CSV file to create.
    """
    if not books:
        logger.info("No book data to save to CSV.")
        return

    try:
        # Get all the unique keys (fields) from all dictionaries
        fieldnames = set()
        for book in books:
            if book:
                fieldnames.update(book.keys())
        fieldnames = sorted(list(fieldnames))
        logger.info(f"CSV fields: {fieldnames}")

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, restval="")
            writer.writeheader()
            for book in books:
                if book is not None:
                    writer.writerow(book)  # Write each book's data

        logger.info(f"Books saved to {filename}")

    except Exception as e:
        logger.error(f"Error saving books to CSV: {e}")


def write_urls(urls_list, log_message, filename):
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["url"])
            for url in urls_list:
                writer.writerow([url])
        logger.info(f"{log_message} {filename}")

    except Exception as e:
        logger.error(f"Error saving failed URLs to CSV: {e}")

def save_failed_urls_to_csv(failed_urls, filename="failed_books.csv"):
    """Saves the failed URLs to a CSV file."""
    if not failed_urls:
        logger.info("No failed URLs to save.")
        return
    write_urls(urls_list=failed_urls, log_message="Failed URLs saved to", filename=filename)


def save_other_links_to_csv(other_links, filename="other_links.csv"):
    """Saves the 'other' links to a CSV file."""
    if not other_links:
        logger.info("No 'other' links to save.")
        return
    write_urls(urls_list=other_links, log_message="Other links saved to", filename=filename)


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


async def main():
    parser = argparse.ArgumentParser(description="Scrape book details from URLs.")
    parser.add_argument("-f", "--file",
                        required=False,
                        help=f"Path to the CSV file containing URLs. Default: {get_default_urls_file()}")
    parser.add_argument("-c", "--csv",
                        action="store_true",
                        help="Output scraped data to CSV files (books.csv, failed_books.csv, other_links.csv).")
    parser.add_argument("-m", "--mongo", action="store_true", help="Output scraped data to a MongoDB database.")
    args = parser.parse_args()  # Keep this outside try-except for standard arg parsing errors

    # Use default URLs file if not specified
    if not args.file:
        args.file = get_default_urls_file()
        logger.info(f"Using default URLs file: {args.file}")

    # Create default URLs file if it doesn't exist
    if not os.path.exists(args.file):
        logger.info(f"URLs file not found at {args.file}. Creating it.")
        if args.file == get_default_urls_file():
            if create_default_urls_file():
                logger.info(f"Created default URLs file at {args.file}")
            else:
                logger.critical(f"Failed to create default URLs file at {args.file}")
                print_log(f"Critical Error: Failed to create default URLs file at {args.file}. Please check permissions.", "error")
                sys.exit(1)
        else:
            logger.critical(f"URLs file not found at {args.file} and it's not the default file.")
            print_log(f"Critical Error: The input file '{args.file}' was not found. Please check the path.", "error")
            sys.exit(1)

    # Pre-flight Checks for Output Destinations
    can_output_to_csv = False
    can_output_to_mongo = False

    print_log("\nRunning pre-flight checks for output destinations...", "info")

    # Check CSV write permissions
    print_log("  Checking CSV write permissions...", "info")
    if check_csv_write_permission('.'):  # Check current directory
        can_output_to_csv = True
        print_log("  CSV write permission: OK", "info")
    else:
        print_log("  CSV write permission: FAILED. CSV output will not be available.", "error")
        # The check_csv_write_permission function already prints an error message

    # Check MongoDB connection
    print_log("  Checking MongoDB connection...", "info")
    if check_mongodb_connection():
        can_output_to_mongo = True
        print_log("  MongoDB connection: OK", "info")
    else:
        print_log("  MongoDB connection: FAILED. MongoDB output will not be available.", "error")
        # The check_mongodb_connection function already prints an error message

    if not can_output_to_csv and not can_output_to_mongo:
        print_log("\nNo valid output destinations available. Please fix permission/MongoDB issues.", "error")
        sys.exit(1)  # Exit if no output option is possible

    # --- Pre-Scrape Output Confirmation with dynamic choices ---
    output_to_csv = args.csv and can_output_to_csv
    output_to_mongo = args.mongo and can_output_to_mongo

    if not output_to_csv and not output_to_mongo:  # Only prompt if no valid flags were passed or if checks failed
        print_log("\nNo valid output destination specified via command line arguments (-c, -m).", "info")
        prompt_options = []
        if can_output_to_csv:
            prompt_options.append("(C)SV")
        if can_output_to_mongo:
            prompt_options.append("(M)ongoDB")

        # Add "Both" if both are available
        if can_output_to_csv and can_output_to_mongo:
            prompt_options.append("(B)oth")

        prompt_options_str = ", ".join(prompt_options)
        prompt_options_str = prompt_options_str.replace(", (B)oth", " or (B)oth")  # Prettier formatting

        while True:
            if not prompt_options:  # Should not happen if previous sys.exit(1) works
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

    # --- Continue with existing logic (URL Reading, Scraping Loop, Final Output Saving) ---

    # Store URLs to scrape within a dictionary
    website_urls = {
        "amazon": [], "packtpub": [], "leanpub": [], "oreilly": [], "other": []
    }
    failed_urls = []

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

    all_urls = []
    batch_size = 10

    for website, urls in website_urls.items():
        if website not in ["other"]:
            print_log(f" {len(urls)} {website.capitalize()} URLs to scrape.", "info")
            all_urls.extend(urls)
        else:
            print_log(f" {len(urls)} {website.capitalize()} URLs will be skipped and added to other_links.csv.", "info")
    total_urls = len(all_urls)

    if total_urls == 0:
        print_log("No valid book URLs found to scrape. Saving skipped links and exiting.", "info")
        save_other_links_to_csv(website_urls["other"])
        sys.exit(0)

    # Playwright Browser Setup and Scraping Loop
    print_log("Starting web scraping operation...", "info")
    async with async_playwright() as p:
        print_log("Opening browser...", "info")
        browser = await p.chromium.launch(headless=True)

        books = []
        start_time = time.time()

        for i in range(0, total_urls, batch_size):
            batch_urls = all_urls[i:i + batch_size]
            print_log(
                f"Starting batch {i // batch_size + 1} of {len(all_urls) // batch_size + (1 if len(all_urls) % batch_size else 0)}",
                "info")

            tasks = []
            for url in batch_urls:
                site = identify_website(url)
                tasks.append(scrape_book(url, browser, site))

            results = await asyncio.gather(*tasks)

            for index, result in enumerate(results):
                if result:
                    books.append(result)
                else:
                    failed_urls.append(batch_urls[index])
                    logger.warning(f"Failed to scrape: {batch_urls[index]}")

            if i + batch_size < total_urls:
                print_log("Pausing between batches...", "info")
                await asyncio.sleep(random.uniform(3, 5))

        print_log("Shutting down browser...", "info")
        total_time = time.time() - start_time
        print_log(
            f"{total_urls} URLs processed in {total_time:.2f} seconds at a rate of {total_time / total_urls:.2f}s per URL",
            "info")

        await browser.close()

    # Output Saving Based on Resolved Choices and pre-flight checks
    if output_to_csv and can_output_to_csv:  # Ensure we can still output to CSV
        print_log("Saving scraped books to CSV files...", "info")
        save_books_to_csv(books)
        save_failed_urls_to_csv(failed_urls)
        save_other_links_to_csv(website_urls["other"])
    else:
        print_log("CSV output not requested or not available.", "info")

    if output_to_mongo and can_output_to_mongo:  # Ensure we can still output to Mongo
        print_log("Saving scraped books to MongoDB...", "info")
        if books:
            save_books_to_mongodb(books)
        else:
            print_log("No books scraped to save to MongoDB.", "info")
    else:
        print_log("MongoDB output not requested or not available.", "info")

    # Always save diagnostic files if any scraping occurred and CSV was not explicitly chosen
    # and CSV output is possible. This is a bit tricky now with dynamic choice.
    # The most robust way is to always try to save failed/other if possible,
    # regardless of the primary output choice.
    if can_output_to_csv:  # Only attempt if write permission exists
        if not output_to_csv:  # If CSV for books wasn't chosen OR wasn't available
            print_log(
                "Saving diagnostic failed/other links to CSV (as primary CSV output for books was not chosen or available).",
                "info")
            save_failed_urls_to_csv(failed_urls)
            save_other_links_to_csv(website_urls["other"])
    else:
        logger.warning("Failed to save diagnostic failed/other links to CSV due to lack of write permissions.")
        print_log("Warning: Failed to save diagnostic failed/other links to CSV due to lack of write permissions.",
                  "warning")


if __name__ == "__main__":
    asyncio.run(main())
