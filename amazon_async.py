import argparse
import asyncio
import csv
from datetime import datetime
import time
import pandas as pd

from playwright.async_api import async_playwright, TimeoutError
import random
from fake_useragent import UserAgent

from src.bookscraper import hash_book
from src.bookscraper.site_constants import amazon_constants
from playwright_stealth import stealth_async


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


def extract_year_from_date(date_string):
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


async def route_handler(route):
    request = route.request
    # if request.resource_type in ["image", "media"]:
    # if "adsystem" in request.url or "partners" in request.url or "media" in request.url:
    if request.resource_type == "document":
        await route.continue_()  # Allow other requests
    else:
        await route.abort()  # Block the request


USER_AGENTS = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",

    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0",

    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15",

    # Edge (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.55",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36 Edg/93.0.961.47",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36 Edg/94.0.992.50",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.40",
]


async def scrape_amazon(url, browser):
    """
    Asynchronously scrapes book details from an Amazon product page.

    This function attempts to extract various details about a book from its Amazon product page,
    including title, authors, ISBN numbers, tags, publication date, and description. It uses
    Playwright for web scraping and implements retry logic for resilience.

    Args:
        url (str): The URL of the Amazon product page to scrape.
        browser (playwright.async_api.Browser): An instance of a Playwright browser to use for scraping.

    Returns:
        dict or None: A dictionary containing the scraped book details if successful, including:
            - url: The original URL of the product page
            - title: The book's title
            - authors: A list of the book's authors
            - isbn10: The book's ISBN-10 number (if available)
            - isbn13: The book's ISBN-13 number (if available)
            - tags: A list of tags or categories associated with the book
            - publication_date: The book's publication date
            - description: A description or summary of the book
            - year: The year of publication extracted from the publication date
            - hash: A unique hash generated from the book's title, authors, and year
        Returns None if scraping fails after all retry attempts.
    """
    retries = 5  # Try three times to fetch the books details, with different user agents
    page = await browser.new_page()

    for attempt in range(retries):
        try:
            # ua = UserAgent(platforms='desktop')
            # chosen_user_agent = ua.random
            chosen_user_agent = random.choice(USER_AGENTS)

            # await stealth_async(page)
            await page.set_extra_http_headers({"User-Agent": chosen_user_agent})

            book_details = {"url": url}

            # Block unnecessary resources
            await page.route("**/*", route_handler)

            print(f"Navigating to {url}")
            await page.goto(url, timeout=30000)

            # Check 404
            try:
                page_title = (await page.title()).lower()
                if "page not found" in page_title:
                    print_log(f"Book not found at {url}", "error")
                    break
            except:
                break

            print(f"Getting title: {url}...")
            try:
                await page.wait_for_selector(amazon_constants.TITLE, timeout=30000)
                title = (await page.locator(amazon_constants.TITLE).inner_text()).strip()
                book_details["title"] = title
            except Exception as e:
                print_log(f"No title for {url}", "error")
                break

            # Get author(s)
            print(f"Getting authors: {url}...")
            try:
                await page.wait_for_selector(amazon_constants.AUTHORS, timeout=1000)
                authors = await page.locator(amazon_constants.AUTHORS).all()
            except TimeoutError:
                authors = await page.locator(amazon_constants.AUTHORS_ALT).all()
            book_details["authors"] = [(await author.inner_text()).strip() for author in authors]

            # Get ISBN10
            byline_info_text = await page.locator("#bylineInfo").inner_text()
            if "Kindle Edition" not in byline_info_text:
                print(f"Getting ISBN10: {url}...")
                try:
                    await page.wait_for_selector(amazon_constants.ISBN10, timeout=5000)
                    isbn10 = (await page.locator(amazon_constants.ISBN10).inner_text()).strip()
                    book_details["isbn10"] = isbn10
                except Exception as e:
                    print_log(f"No ISBN10 for {url}", "error")

                # Get ISBN13
                print(f"Getting ISBN13: {url}...")
                try:
                    isbn13 = (await page.locator(amazon_constants.ISBN13).inner_text()).strip()
                    book_details["isbn13"] = isbn13
                except Exception as e:
                    print_log(f"No ISBN13 for {url}", "error")

            # Get Book Tags
            print(f"Getting tags: {url}...")
            try:
                book_tags = await page.locator(amazon_constants.TAGS).all()
                book_details["tags"] = [
                    (await tag.inner_text()).replace("(Books)", "").strip() for tag in book_tags]
            except Exception as e:
                print_log(f"No tags for {url}", "error")

            # Get Publication Date
            try:
                print(f"Getting publication date: {url}...")
                pd = (await page.locator(amazon_constants.PUBLICATION_DATE).inner_text()).strip()
                if pd:
                    book_details["publication_date"] = pd
                else:
                    try:
                        # Expand Details pane - Amazon Specific
                        await page.click(amazon_constants.DETAILS_BUTTON)
                        await page.wait_for_selector(amazon_constants.PUBLICATION_DATE, state="attached")
                        book_details["publication_date"] = (await page.locator(
                            amazon_constants.PUBLICATION_DATE).inner_text()).strip()
                    except:
                        pass
            except Exception as e:
                print_log(f"Error getting publication date for {url}: {e}", "error")

            # Scrape Description
            try:
                print(f"Getting description: {url}...")
                description = (await page.locator(amazon_constants.DESCRIPTION).inner_text()).strip()
                book_details["description"] = description
            except Exception as e:
                print_log(f"No description for {url}", "error")

            year = extract_year_from_date(book_details.get("publication_date"))
            book_details["year"] = year
            book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)

            # Close the page and return book details
            await page.close()
            return book_details

        except TimeoutError:
            print_log(f"Timeout on {url}, retrying...", "error")
            await asyncio.sleep(2 ** attempt)

        except Exception as e:
            print_log(f"Error on {url}: {e}, retrying...", "error")
            await asyncio.sleep(2 ** attempt)

    print_log(f"Failed to scrape {url} after {retries} retries.", "error")
    await page.close()  # close the page if all retries fail.
    return None


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

    amazon_urls = []  # Initialize an empty list for Amazon books
    packtpub_urls = []  # Initialize an empty list for Packtpub books
    leanpub_urls = []  # Initialize an empty list for Leanpub books
    oreilly_urls = []  # Initialize an empty list for O'Reilly books
    other_urls = []  # Initialize an empty list for other books (PDFs, portals, etc.)
    failed_urls = []  # Initialize an empty list for failed books

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

    batch_size = 10
    total_urls = len(amazon_urls)

    async with async_playwright() as p:
        print("Opening browser")
        browser = await p.chromium.launch(headless=True)

        books = []
        start = time.time()

        for i in range(0, total_urls, batch_size):
            batch_urls = amazon_urls[i:i + batch_size]
            print(f"Starting batch {i // batch_size + 1}")

            tasks = []
            for url in batch_urls:
                tasks.append(scrape_amazon(url, browser))

            results = await asyncio.gather(*tasks)

            for index, result in enumerate(results):
                if result:
                    books.append(result)
                else:
                    failed_urls.append(batch_urls[index])
                    print(f"Failed urls: {failed_urls}")

            if i + batch_size < total_urls:
                print("Pausing between batches...")
                await asyncio.sleep(random.uniform(3, 5))  # Pause between batches
        print("Shutting down browser...")
        print(f"Time elapsed: {time.time() - start} seconds")

        await browser.close()

    save_books_to_csv(books)
    save_failed_urls_to_csv(failed_urls)


if __name__ == "__main__":
    asyncio.run(main())
