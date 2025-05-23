import asyncio
import random
import logging

from .book_utils import hash_book, extract_year_from_date, print_log

from .parameters import USER_AGENTS, site_constants

# Get a logger instance specifically for this module
module_logger = logging.getLogger('bookscraper.scrape_details')


async def route_handler(route):
    request = route.request
    if request.resource_type == "document":
        await route.continue_()  # Allow other requests
    else:
        await route.abort()  # Block the request


async def scrape_book(url: str, browser, site: str):
    retries = 5  # Number of retries for scraping a single URL
    page = await browser.new_page()

    constants = site_constants.get(site)
    if not constants:
        module_logger.error(
            f"No site constants found for site: {site} for URL: {url}. Please add scraping selectors to parameters.py.")
        await page.close()
        return None

    for attempt in range(1, retries + 1):
        try:
            chosen_user_agent = random.choice(USER_AGENTS)
            await page.set_extra_http_headers({"User-Agent": chosen_user_agent})
            await page.route("**/*", route_handler)  # Block unnecessary resources

            print_log(f"Navigating to {url} (Attempt {attempt}/{retries})", "info")
            module_logger.info(f"Attempting to scrape {url}.")
            await page.goto(url, timeout=40000)

            # Check 404
            page_title = (await page.title()).lower()
            if site == "oreilly" and len(page_title) == 0:
                print_log(f"Book not found at {url} (404 - Oreilly). Skipping.", "error")
                module_logger.warning(f"404 page detected for Oreilly URL: {url}")
                await page.close()  # Close page on permanent failure
                return None
            if site != "oreilly" and constants["404_PAGE_TITLE"] in page_title:
                print_log(f"Book not found at {url} (404 - {site}). Skipping.", "error")
                module_logger.warning(f"404 page detected for {site} URL: {url}")
                await page.close()  # Close page on permanent failure
                return None

            book_details = {"url": url, "site": site}

            if site == "amazon":
                book_details = await scrape_amazon_details(page, url, book_details, constants)
            elif site == "packtpub":
                book_details = await scrape_packtpub_details(page, url, book_details, constants)
            elif site == "leanpub":
                book_details = await scrape_leanpub_details(page, url, book_details, constants)
            elif site == "oreilly":
                book_details = await scrape_oreilly_details(page, url, book_details, constants)
            else:
                module_logger.warning(f"Unsupported site '{site}' for URL: {url}. Skipping details scraping.")
                await page.close()
                return None

            if book_details:
                module_logger.info(f"Successfully scraped details for: {url}")
                await page.close()
                return book_details
            else:
                module_logger.warning(f"No book details returned for {url} after scraping attempt {attempt}.")
                continue  # Continue to next attempt if book_details is None

        except TimeoutError:
            print_log(f"Timeout on {url}, retrying (Attempt {attempt}/{retries})", "error")
            module_logger.error(f"Timeout occurred for {url} on attempt {attempt}.")
            await asyncio.sleep(random.uniform(2, 4) * attempt)  # Exponential backoff with random jitter

        except Exception as e:
            print_log(f"Error on {url}: {e}. Retrying (Attempt {attempt}/{retries})", "error")
            module_logger.exception(
                f"An unexpected error occurred for {url} on attempt {attempt}.")  # Uses exception for traceback
            await asyncio.sleep(random.uniform(2, 4) * attempt)  # Exponential backoff with random jitter

    print_log(f"Failed to scrape {url} after {retries} retries. Giving up.", "error")
    module_logger.critical(f"Permanently failed to scrape {url} after {retries} attempts.")
    await page.close()  # close the page if all retries fail.
    return None


async def scrape_amazon_details(page, url, book_details, constants):
    module_logger.info(f"Scraping Amazon details for: {url}")
    try:
        await page.wait_for_selector(constants["BOOK_TITLE"], timeout=30000)
        title = (await page.locator(constants["BOOK_TITLE"]).inner_text()).strip()
        book_details["title"] = title
        module_logger.info(f"Found title for {url}: {title}")
    except Exception as e:
        module_logger.warning(f"No title found for {url}: {e}")
        print_log(f"No title found for {url}. Skipping this book.", "error")
        return None

    # Get author(s)
    module_logger.info(f"Getting authors for: {url}")
    try:
        authors_elements = []
        if await page.locator(constants["AUTHORS"]).count() > 0:
            authors_elements = await page.locator(constants["AUTHORS"]).all()
        elif await page.locator(constants["AUTHORS_ALT"]).count() > 0:
            authors_elements = await page.locator(constants["AUTHORS_ALT"]).all()
        book_details["authors"] = [(await author.inner_text()).strip() for author in authors_elements]
        module_logger.info(f"Found authors for {url}: {book_details['authors']}")
    except Exception as e:
        module_logger.warning(f"Error getting authors for {url}: {e}. Setting to empty list.")
        book_details["authors"] = []
        print_log(f"No authors found for {url}.", "warning")

    # Get ISBN10/ISBN13
    try:
        byline_info_text = await page.locator("#bylineInfo").inner_text()
        if "Kindle Edition" not in byline_info_text:
            module_logger.info(f"Getting ISBNs for: {url} (Non-Kindle)")
            try:
                await page.wait_for_selector(constants["ISBN10"], timeout=5000)
                isbn10 = (await page.locator(constants["ISBN10"]).inner_text()).strip()
                book_details["isbn10"] = isbn10
                module_logger.info(f"Found ISBN10 for {url}: {isbn10}")
            except Exception:
                module_logger.info(f"No ISBN10 found for {url}.")  # Not an error, just absent

            try:
                isbn13 = (await page.locator(constants["ISBN13"]).inner_text()).strip()
                book_details["isbn13"] = isbn13
                module_logger.info(f"Found ISBN13 for {url}: {isbn13}")
            except Exception:
                module_logger.info(f"No ISBN13 found for {url}.")
        else:
            module_logger.info(f"Kindle Edition detected for {url}. Skipping ISBN extraction.")
    except Exception as e:
        module_logger.warning(f"Could not determine if Kindle edition for {url}: {e}. Skipping ISBNs.")

    # Get Book Tags
    module_logger.info(f"Getting tags for: {url}")
    try:
        book_tags = await page.locator(constants["TAGS"]).all()
        book_details["tags"] = [
            (await tag.inner_text()).replace("(Books)", "").strip() for tag in book_tags]
        module_logger.info(f"Found tags for {url}: {book_details['tags']}")
    except Exception as e:
        module_logger.warning(f"No tags found for {url}: {e}. Setting to empty list.")
        book_details["tags"] = []

    # Get Publication Date
    module_logger.info(f"Getting publication date for: {url}")
    try:
        pd = (await page.locator(constants["PUBLICATION_DATE"]).inner_text()).strip()
        if pd:
            book_details["publication_date"] = pd
            module_logger.info(f"Found publication date (initial) for {url}: {pd}")
        else:
            module_logger.info(f"No initial publication date found for {url}. Trying details button.")
            await page.click(constants["DETAILS_BUTTON"])
            await page.wait_for_selector(constants["PUBLICATION_DATE"], state="attached", timeout=5000)  # Added timeout
            book_details["publication_date"] = (await page.locator(
                constants["PUBLICATION_DATE"]).inner_text()).strip()
            module_logger.info(f"Found publication date (after expand) for {url}: {book_details['publication_date']}")
    except Exception as e:
        module_logger.warning(f"Error getting publication date for {url}: {e}.")
        print_log(f"No publication date for {url}.", "warning")

    # Scrape Description
    module_logger.info(f"Getting description for: {url}")
    try:
        # Check if "Read more" link exists and click it if so
        read_more_link = page.locator(constants["READ_MORE_LINK"])
        if await read_more_link.is_visible():
            await read_more_link.click()
            # module_logger.info(f"Clicked 'Read more' for description on {url}")  # Verbose
            await page.wait_for_timeout(500)  # Small pause for content to expand

        description = (await page.locator(constants["DESCRIPTION"]).inner_text()).strip()
        book_details["description"] = description
        module_logger.info(f"Found description for {url} (length: {len(description) if description else 0})")
    except Exception as e:
        module_logger.warning(f"No description found for {url}.")

    year = extract_year_from_date(book_details.get("publication_date"))
    book_details["year"] = year
    book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)

    return book_details


async def scrape_leanpub_details(page, url, book_details, constants):
    module_logger.info(f"Scraping Leanpub details for: {url}")
    try:
        await page.wait_for_selector(constants["BOOK_TITLE"], timeout=30000)
        title = (await page.locator(constants["BOOK_TITLE"]).inner_text()).strip()
        book_details["title"] = title
        module_logger.info(f"Found title for {url}: {title}")
    except Exception as e:
        module_logger.warning(f"No title found for {url}: {e}. Skipping this book.")
        return None

    # Get author(s)
    module_logger.info(f"Getting authors for: {url}")
    try:
        authors_elements = []
        try:
            await page.wait_for_selector(constants["AUTHORS"], timeout=2000)
            authors_elements = await page.locator(constants["AUTHORS"]).all()
        except TimeoutError:
            if constants["AUTHORS_ALT"]:  # Check if alternative exists
                authors_elements = await page.locator(constants["AUTHORS_ALT"]).all()
        author_names = []
        for author in authors_elements:
            author_name = (await author.inner_text()).strip()
            if author_name not in author_names:
                author_names.append(author_name)
        book_details["authors"] = author_names
        module_logger.info(f"Found authors for {url}: {book_details['authors']}")
    except Exception as e:
        module_logger.warning(f"Error getting authors for {url}: {e}. Setting to empty list.")
        book_details["authors"] = []

    # Get Book Tags
    module_logger.info(f"Getting tags for: {url}")
    try:
        book_tags = await page.locator(constants["TAGS"]).all()
        book_details["tags"] = [await tag.inner_text() for tag in book_tags]
        module_logger.info(f"Found tags for {url}: {book_details['tags']}")
    except Exception as e:
        module_logger.warning(f"No tags found for {url}: {e}. Setting to empty list.")
        book_details["tags"] = []

    # Get Publication Date
    module_logger.info(f"Getting publication date for: {url}")
    try:
        pd = (await page.locator(constants["PUBLICATION_DATE"]).inner_text()).lower().replace("last updated on",
                                                                                              "").strip()
        if pd:
            book_details["publication_date"] = pd
            module_logger.info(f"Found publication date for {url}: {pd}")
    except Exception as e:
        module_logger.warning(f"Error getting publication date for {url}: {e}.")

    # Scrape Description
    module_logger.info(f"Getting description for: {url}")
    try:
        description = None
        if await page.locator(constants["DESCRIPTION"]).count() > 0:
            description = (await page.locator(constants["DESCRIPTION"]).inner_text()).strip()
        elif await page.locator(constants["DESCRIPTION_ALT"]).count() > 0:
            description = (await page.locator(constants["DESCRIPTION_ALT"]).inner_text()).strip()

        book_details["description"] = description
        module_logger.info(f"Found description for {url} (length: {len(description) if description else 0})")
    except Exception as e:
        module_logger.warning(f"No description found for {url}: {e}.")

    year = extract_year_from_date(book_details.get("publication_date"))
    book_details["year"] = year
    book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)

    return book_details


async def scrape_packtpub_details(page, url, book_details, constants):
    module_logger.info(f"Scraping Packtpub details for: {url}")
    try:
        await page.wait_for_selector(constants["BOOK_TITLE"], timeout=30000)
        title = (await page.locator(constants["BOOK_TITLE"]).inner_text()).strip()
        book_details["title"] = title
        module_logger.info(f"Found title for {url}: {title}")
    except Exception as e:
        module_logger.warning(f"No title found for {url}: {e}. Skipping this book.")
        return None

    # Get author(s)
    module_logger.info(f"Getting authors for: {url}")
    try:
        authors_elements = await page.locator(constants["AUTHORS"]).all()
        author_names = []
        for author in authors_elements:
            author_name = (await author.inner_text()).strip()
            if author_name not in author_names:
                author_names.append(author_name)
        book_details["authors"] = author_names
        module_logger.info(f"Found authors for {url}: {book_details['authors']}")
    except Exception as e:  # Changed to general Exception as TimeoutError might not be specific enough for general failures
        module_logger.warning(f"Could not find authors for {url}: {e}. Setting to empty list.")
        book_details["authors"] = []

    # Get ISBN13
    module_logger.info(f"Getting ISBN13 for: {url}")
    try:
        # Check if ISBN13 selector exists before trying to get text
        if await page.locator(constants["ISBN13"]).count() > 0:
            isbn13 = (await page.locator(constants["ISBN13"]).inner_text()).strip()
            book_details["isbn13"] = isbn13
            module_logger.info(f"Found ISBN13 for {url}: {isbn13}")
        else:
            module_logger.info(f"No ISBN13 element found for {url}.")
    except Exception as e:
        module_logger.warning(f"Error getting ISBN13 for {url}: {e}.")

    # Get Book Tags
    module_logger.info(f"Getting tags for: {url}")
    try:
        book_tags = await page.locator(constants["TAGS"]).all_text_contents()
        book_details["tags"] = [tag.strip() for tag in book_tags]
        module_logger.info(f"Found tags for {url}: {book_details['tags']}")
    except Exception as e:
        module_logger.warning(f"No tags found for {url}: {e}. Setting to empty list.")
        book_details["tags"] = []

    # Get Publication Date
    module_logger.info(f"Getting publication date for: {url}")
    try:
        pd_elements = await page.locator(constants["PUBLICATION_DATE"]).all()
        publication_date_found = False
        for element in pd_elements:
            if await element.is_visible():
                publication_date = await element.inner_text()
                book_details["publication_date"] = publication_date
                module_logger.info(f"Found publication date for {url}: {publication_date}")
                publication_date_found = True
                break
        if not publication_date_found:
            module_logger.info(f"No visible publication date element found for {url}.")
    except Exception as e:
        module_logger.warning(f"Error getting publication date for {url}: {e}.")

    # Scrape Description
    module_logger.info(f"Getting description for: {url}")
    try:
        description = (await page.locator(constants["DESCRIPTION"]).inner_text()).strip()
        book_details["description"] = description
        module_logger.info(f"Found description for {url} (length: {len(description) if description else 0})")
    except Exception as e:
        module_logger.warning(f"No description found for {url}: {e}.")
        return None  # Considered essential for Packtpub, so return None if missing.

    year = extract_year_from_date(book_details.get("publication_date"))
    book_details["year"] = year
    book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)

    return book_details


async def scrape_oreilly_details(page, url, book_details, constants):
    module_logger.info(f"Scraping O'Reilly details for: {url}")
    try:
        book_details["title"] = (await page.locator(constants["BOOK_TITLE"]).inner_text()).strip()
        module_logger.info(f"Found title for {url}: {book_details['title']}")
    except Exception as e:
        module_logger.warning(f"No title found for {url}: {e}. Skipping this book.")
        return None

    # Get author(s)
    module_logger.info(f"Getting authors for: {url}")
    try:
        authors_elements = await page.locator(constants["AUTHORS"]).all()
        author_names = []
        for author in authors_elements:
            author_name = (await author.inner_text()).strip()
            if author_name not in author_names:
                author_names.append(author_name)
        book_details["authors"] = author_names
        module_logger.info(f"Found authors for {url}: {book_details['authors']}")
    except Exception as e:  # Catch any exception, not just TimeoutError
        module_logger.warning(f"No authors found for {url}: {e}. Setting to empty list.")
        book_details["authors"] = []

    # ISBN10 and ISBN13 use the same field for O'Reilly
    module_logger.info(f"Getting ISBN for: {url}")
    try:
        isbn_locator = page.locator(constants["ISBN"].strip())
        isbn = (await isbn_locator.text_content()).replace("ISBN: ", "").strip()  # Ensure stripping
        module_logger.info(f"Raw ISBN for {url}: {isbn}")
        if len(isbn) == 10:
            book_details["isbn10"] = isbn
            module_logger.info(f"Identified ISBN10 for {url}: {isbn}")
        elif len(isbn) == 13:
            book_details["isbn13"] = isbn
            module_logger.info(f"Identified ISBN13 for {url}: {isbn}")
        else:
            module_logger.warning(f"Invalid ISBN length ({len(isbn)}) for {url}: {isbn}")
    except Exception as e:
        module_logger.warning(f"No ISBN found for {url}: {e}.")

    # Get Publication Date
    module_logger.info(f"Getting publication date for: {url}")
    try:
        pd_locator = page.locator(constants["PUBLICATION_DATE"].strip())
        pd = (await pd_locator.text_content()).strip()  # Ensure stripping
        if pd:
            book_details["publication_date"] = pd
            module_logger.info(f"Found publication date for {url}: {pd}")
    except Exception as e:
        module_logger.warning(f"Error getting publication date for {url}: {e}.")

    # Scrape Description
    module_logger.info(f"Getting description for: {url}")
    try:
        # Using filter with has_text can be very specific, make sure it's robust
        description_locator = page.locator("div.title-description div.content span")
        # Try to find a span with significant text, or the first one if not specific
        if await description_locator.count() > 0:
            # You might need a more general selector or logic here if the specific "To say that C++ programmers" isn't always present
            # A common strategy is to get all relevant spans and join them
            description_elements = await description_locator.all_inner_texts()
            description = "\n".join([d.strip() for d in description_elements if d.strip()])
        else:
            description = None

        if description:
            book_details["description"] = description
            module_logger.info(f"Found description for {url} (length: {len(description)})")
        else:
            module_logger.warning(f"No significant description found for {url}.")

    except Exception as e:
        module_logger.warning(f"Error getting description for {url}: {e}.")

    year = extract_year_from_date(book_details.get("publication_date"))
    book_details["year"] = year
    book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)

    return book_details
