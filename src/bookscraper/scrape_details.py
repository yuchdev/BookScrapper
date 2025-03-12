import asyncio
import random

# from fake_useragent import UserAgent
# from playwright_stealth import stealth_async, stealth_sync

from .book_utils import hash_book, extract_year_from_date, print_log

from .parameters import USER_AGENTS, site_constants


async def route_handler(route):
    request = route.request
    # if request.resource_type in ["image", "media"]:
    # if "adsystem" in request.url or "partners" in request.url or "media" in request.url:
    if request.resource_type == "document":
        await route.continue_()  # Allow other requests
    else:
        await route.abort()  # Block the request


async def scrape_book(url: str, browser, site: str):
    retries = 5  # Try three times to fetch the books details, with different user agents
    page = await browser.new_page()

    constants = site_constants.get(site)

    for attempt in range(retries):
        try:
            # ua = UserAgent(platforms='desktop')
            # chosen_user_agent = ua.random
            chosen_user_agent = random.choice(USER_AGENTS)
            # await stealth_async(page)
            await page.set_extra_http_headers({"User-Agent": chosen_user_agent})
            await page.route("**/*", route_handler)  # Block unnecessary resources

            print(f"Navigating to {url}")
            await page.goto(url, timeout=40000)

            # Check 404
            page_title = (await page.title()).lower()
            if site == "oreilly" and len(page_title) == 0:
                print(f"Book not found at {url} (404 - Oreilly)")
                return None
            if site != "oreilly" and constants["404_PAGE_TITLE"] in page_title:
                print(f"Book not found at {url} (404 - General)")
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

            # Close the page and return book details
            if book_details:
                await page.close()
                return book_details

        except TimeoutError:
            print_log(f"Timeout on {url}, retrying", "error")
            await asyncio.sleep(2 ** attempt)

        except Exception as e:
            print_log(f"Error on {url}: {e}. Retrying", "error")
            await asyncio.sleep(2 ** attempt)

    print_log(f"Failed to scrape {url} after {retries} retries.", "error")
    await page.close()  # close the page if all retries fail.
    return None


async def scrape_amazon_details(page, url, book_details, constants):
    print(f"Getting title: {url}")
    try:
        await page.wait_for_selector(constants["BOOK_TITLE"], timeout=30000)
        title = (await page.locator(constants["BOOK_TITLE"]).inner_text()).strip()
        book_details["title"] = title
    except Exception as e:
        print_log(f"No title for {url}", "error")
        return None

    # Get author(s)
    print(f"Getting authors: {url}")
    try:
        if await page.locator(constants["AUTHORS"]).count() > 0:
            authors = await page.locator(constants["AUTHORS"]).all()
        else:
            authors = await page.locator(constants["AUTHORS_ALT"]).all()
        book_details["authors"] = [(await author.inner_text()).strip() for author in authors]

    except Exception as e:
        print_log(f"Error getting authors for {url}: {e}", "error")
        book_details["authors"] = []

    # Get ISBN10
    byline_info_text = await page.locator("#bylineInfo").inner_text()
    if "Kindle Edition" not in byline_info_text:
        print(f"Getting ISBN10: {url}")
        try:
            await page.wait_for_selector(constants["ISBN10"], timeout=5000)
            isbn10 = (await page.locator(constants["ISBN10"]).inner_text()).strip()
            book_details["isbn10"] = isbn10
        except Exception as e:
            print_log(f"No ISBN10 for {url}", "error")

        # Get ISBN13
        print(f"Getting ISBN13: {url}")
        try:
            isbn13 = (await page.locator(constants["ISBN13"]).inner_text()).strip()
            book_details["isbn13"] = isbn13
        except Exception as e:
            print_log(f"No ISBN13 for {url}", "error")

    # Get Book Tags
    print(f"Getting tags: {url}")
    try:
        book_tags = await page.locator(constants["TAGS"]).all()
        book_details["tags"] = [
            (await tag.inner_text()).replace("(Books)", "").strip() for tag in book_tags]
    except Exception as e:
        print_log(f"No tags for {url}", "error")

    # Get Publication Date
    try:
        print(f"Getting publication date: {url}")
        pd = (await page.locator(constants["PUBLICATION_DATE"]).inner_text()).strip()
        if pd:
            book_details["publication_date"] = pd
        else:
            try:
                # Expand Details pane - Amazon Specific
                await page.click(constants["DETAILS_BUTTON"])
                await page.wait_for_selector(constants["PUBLICATION_DATE"], state="attached")
                book_details["publication_date"] = (await page.locator(
                    constants["PUBLICATION_DATE"]).inner_text()).strip()
            except:
                pass
    except Exception as e:
        print_log(f"Error getting publication date for {url}: {e}", "error")

    # Scrape Description
    try:
        print(f"Getting description: {url}")
        description = (await page.locator(constants["DESCRIPTION"]).inner_text()).strip()
        book_details["description"] = description
    except Exception as e:
        print_log(f"No description for {url}", "error")

    year = extract_year_from_date(book_details.get("publication_date"))
    book_details["year"] = year
    book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)

    return book_details


async def scrape_leanpub_details(page, url, book_details, constants):
    print(f"Getting title: {url}")
    try:
        await page.wait_for_selector(constants["BOOK_TITLE"], timeout=30000)
        title = (await page.locator(constants["BOOK_TITLE"]).inner_text()).strip()
        book_details["title"] = title
    except Exception as e:
        print_log(f"No title for {url}", "error")
        return None

    # Get author(s)
    print(f"Getting authors: {url}")
    try:
        await page.wait_for_selector(constants["AUTHORS"], timeout=2000)
        authors = await page.locator(constants["AUTHORS"]).all()
    except TimeoutError:
        authors = await page.locator(constants["AUTHORS_ALT"]).all()
    author_names = []
    for author in authors:
        author_name = (await author.inner_text()).strip()
        if author_name not in author_names:
            author_names.append(author_name)
    book_details["authors"] = author_names

    # ISBN10 and ISBN13 are optional and therefore rarely used on leanpub

    # Get Book Tags
    print(f"Getting tags: {url}")
    try:
        book_tags = await page.locator(constants["TAGS"]).all()
        book_details["tags"] = [await tag.inner_text() for tag in book_tags]
    except Exception as e:
        print_log(f"No tags for {url}: {e}", "error")
        book_details["tags"] = []

    # Get Publication Date
    try:
        print(f"Getting publication date: {url}")
        pd = (await page.locator(constants["PUBLICATION_DATE"]).inner_text()).lower().replace("last updated on",
                                                                                              "").strip()
        if pd:
            book_details["publication_date"] = pd
    except Exception as e:
        print_log(f"Error getting publication date for {url}: {e}", "error")

    # Scrape Description
    try:
        print(f"Getting description: {url}")
        if await page.locator(constants["DESCRIPTION"]).count() > 0:
            description = (await page.locator(constants["DESCRIPTION"]).inner_text()).strip()
        elif await page.locator(constants["DESCRIPTION_ALT"]).count() > 0:
            description = (await page.locator(constants["DESCRIPTION_ALT"]).inner_text()).strip()
        else:
            description = None
        book_details["description"] = description
    except Exception as e:
        print_log(f"No description for {url}", "error")

    year = extract_year_from_date(book_details.get("publication_date"))
    book_details["year"] = year
    book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)

    return book_details


async def scrape_packtpub_details(page, url, book_details, constants):
    print(f"Getting title: {url}")
    try:
        await page.wait_for_selector(constants["BOOK_TITLE"], timeout=30000)
        title = (await page.locator(constants["BOOK_TITLE"]).inner_text()).strip()
        book_details["title"] = title
    except Exception as e:
        print_log(f"No title for {url}", "error")
        return None

    # Get author(s)
    print(f"Getting authors: {url}")
    try:
        authors = await page.locator(constants["AUTHORS"]).all()
        author_names = []
        for author in authors:
            author_name = (await author.inner_text()).strip()
            if author_name not in author_names:
                author_names.append(author_name)
        book_details["authors"] = author_names
    except TimeoutError as e:
        print_log("Could not find authors for {url}: {e}", "error")

    # ISBN10 and ISBN13 are optional and therefore rarely used on leanpub

    # Get Book Tags
    print(f"Getting tags: {url}")
    try:
        book_tags = await page.locator(constants["TAGS"]).all_text_contents()
        book_details["tags"] = [tag.strip() for tag in book_tags]
    except Exception as e:
        print_log(f"No tags for {url}: {e}", "error")
        book_details["tags"] = []

    # Get Publication Date
    try:
        print(f"Getting publication date: {url}")
        pd_elements = await page.locator(constants["PUBLICATION_DATE"]).all()

        for element in pd_elements:
            if await element.is_visible():
                publication_date = await element.inner_text()
                book_details["publication_date"] = publication_date

    except Exception as e:
        print_log(f"Error getting publication date for {url}: {e}", "error")

    # Scrape Description
    try:
        print(f"Getting description: {url}")
        description = (await page.locator(constants["DESCRIPTION"]).inner_text()).strip()
        book_details["description"] = description
    except Exception as e:
        print_log(f"No description for {url}", "error")
        return None

    year = extract_year_from_date(book_details.get("publication_date"))
    book_details["year"] = year
    book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)

    return book_details


async def scrape_oreilly_details(page, url, book_details, constants):
    print(f"Getting title: {url}")
    try:
        book_details["title"] = (await page.locator(constants["BOOK_TITLE"]).inner_text()).strip()
    except Exception as e:
        print_log(f"No title for {url}", "error")
        return None

    # Get author(s)
    print(f"Getting authors: {url}")
    try:
        authors = await page.locator(constants["AUTHORS"]).all()
        author_names = []
        for author in authors:
            author_name = (await author.inner_text()).strip()
            if author_name not in author_names:
                author_names.append(author_name)
        book_details["authors"] = author_names
    except TimeoutError:
        book_details["authors"] = []

    # ISBN10 and ISBN13 use the same field for O'Reilly
    print(f"Getting ISBN: {url}")
    isbn_locator = page.locator(constants["ISBN"].strip())  # create the locator object.
    isbn = (await isbn_locator.text_content()).replace("ISBN: ", "")  # await the text_content method.
    print(f"isbn: {isbn}")
    if len(isbn) == 10:
        book_details["isbn10"] = isbn
    elif len(isbn) == 13:
        book_details["isbn13"] = isbn

    # No tags or categories for O'Reilly

    # Get Publication Date
    try:
        print(f"Getting publication date: {url}")
        pd_locator = page.locator(constants["PUBLICATION_DATE"].strip())
        pd = (await pd_locator.text_content())
        print(pd)
        if pd:
            book_details["publication_date"] = pd
    except Exception as e:
        print_log(f"Error getting publication date for {url}: {e}", "error")

    # Scrape Description
    try:
        print(f"Getting description: {url}")
        description_locator = page.locator("div.title-description div.content span").filter(
            has_text="To say that C++ programmers")
        await description_locator.wait_for()
        description = await description_locator.inner_text()
        print(f"Description:\n{description}")
        book_details["description"] = description
    except Exception as e:
        print_log(f"No description for {url}, error: {e}", "error")

    year = extract_year_from_date(book_details.get("publication_date"))
    book_details["year"] = year
    book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)

    return book_details
