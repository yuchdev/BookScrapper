import asyncio
import random

# from fake_useragent import UserAgent
# from playwright_stealth import stealth_async, stealth_sync

from .book_utils import hash_book, extract_year_from_date, print_log
from .site_constants import amazon_constants
from .site_constants.user_agents import USER_AGENTS


async def route_handler(route):
    request = route.request
    # if request.resource_type in ["image", "media"]:
    # if "adsystem" in request.url or "partners" in request.url or "media" in request.url:
    if request.resource_type == "document":
        await route.continue_()  # Allow other requests
    else:
        await route.abort()  # Block the request


# def get_random_user_agent():
#     user_agents = [
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
#         "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15; rv:109.0) Gecko/20100101 Firefox/111.0",
#         "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0",
#         # Add more realistic User-Agents
#     ]
#     return random.choice(user_agents)


# def get_site(url: str) -> str:
#     site_pattern = r"(?://(.+?)/)"
#     try:
#         match = re.findall(site_pattern, url)
#         if match:
#             return match[0]
#         else:
#             return ''
#     except Exception as e:
#         site = ''
#         print(f"Error occurred while parsing URL: {e}")


# def scrape_packtpub(url: str, page):
#     try:
#         print(f"Opening {url}...")
#         page.goto(url, timeout=10000)
#         print("Waiting for elements to load...")
#
#         page.wait_for_selector("h1.product-title", state="attached", timeout=3000)
#
#         book_details = {"url": url, "site": "packtpub.com"}
#
#         # Scrape Title
#         try:
#             print("Getting book title...")
#             book_details["title"] = page.locator("h1.product-title").inner_text().strip()
#         except Exception as e:
#             print(f"Failed to get book at {url}. Check link.")
#             return
#
#         # Scrape Authors
#         try:
#             print("Getting book author(s)...")
#             page.wait_for_selector('.authors .authors-dark', timeout=10000)  # Wait for authors
#
#             author_elements = page.locator('.authors .authors-dark').all()
#             author_names = set()  # Use a set to store unique author names
#
#             for author_element in author_elements:
#                 author_name = author_element.inner_text().strip()
#                 author_names.add(author_name)
#
#             book_details['authors'] = list(author_names)  # Convert the set back to a list
#         except Exception as e:
#             print(f"Error getting authors: {e}")
#             book_details["authors"] = None
#
#         # Scrape isbn13
#         try:
#             print("Getting book isbn13...")
#             isbn_parent = page.get_by_text("ISBN-13 :").locator("..")  # ".." goes to the parent element
#             isbn_value_element = isbn_parent.locator("*").nth(1)  # * selects all children, nth(1) gets the second one
#             book_details['isbn13'] = isbn_value_element.inner_text().strip()
#         except:
#             book_details["isbn13"] = None
#
#         # Scrape Book Tags
#         try:
#             print("Getting book tags...")
#             tag_parent = page.get_by_text("Category :").locator("..")  # ".." goes to the parent element
#             tag_value_element = tag_parent.locator("*").nth(1)  # * selects all children, nth(1) gets the second one
#             book_details['tags'] = tag_value_element.inner_text().strip()
#         except:
#             book_details["tags"] = []
#
#         # Scrape Publication Date
#         try:
#             print("Getting book publication date...")
#             pub_date_parent = page.get_by_text("Publication date :").locator("..")  # ".." goes to the parent element
#             pub_date_value_element = pub_date_parent.locator("*").nth(
#                 1)  # * selects all children, nth(1) gets the second one
#             book_details['publication_date'] = pub_date_value_element.inner_text().strip()
#         except:
#             book_details["publication_date"] = None
#
#         # Scrape Summary
#         try:
#             print("Getting book summary...")
#             description_element = page.locator('.product-book-content-details .content-text').nth(
#                 1)  # Select the 2nd .content-text (description)
#             book_details['description'] = description_element.inner_text().strip()
#         except Exception as e:
#             print(f"Error getting summary: {e}")
#             book_details['summary'] = None
#
#         # Extract Year from Publication Date and create book hash
#         year = extract_year_from_date(book_details.get("publication_date"))
#         book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)  # Use get
#
#         return book_details
#
#     except Exception as e:
#         print(f"Error scraping book details: {e} Please check {url}.")
#         return None


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
                await page.wait_for_selector(amazon_constants.AUTHORS, timeout=2000)
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


def scrape_leanpub(url: str, page):
    try:
        print(f"Opening {url}...")
        page.goto(url, timeout=10000)
        print("Waiting for elements to load...")

        page.wait_for_selector(".book-hero__title", state="attached", timeout=10000)

        book_details = {}
        book_details["url"] = url
        book_details["site"] = "leanpub.com"

        # Scrape Title
        try:
            print("Getting book title...")
            title_element = page.locator('.book-hero__title')  # Locate the title element
            title_text = title_element.inner_text().strip()  # Extract and clean the text
            book_details["title"] = title_text
        except Exception as e:
            print(f"Failed to get book at {url}. Check link.")
            return

        # Scrape Authors
        try:
            print("Getting book author(s)...")
            author_elements = page.locator('.avatar-with-name__name').all()
            author_names = set()  # Use a set to store unique author names

            for author_element in author_elements:
                author_name = author_element.inner_text().strip()
                author_names.add(author_name)

            book_details['authors'] = list(author_names)  # Convert the set back to a list
        except Exception as e:
            print(f"Error getting authors: {e}")
            book_details["authors"] = None

            # No isbn10 or isbn13
            book_details["isbn10"] = None
            book_details["isbn13"] = None

        # Scrape Book Tags
        try:
            print("Getting book tags...")
            category_elements = page.locator('.meta-list__item.categories li')  # Locate the <li> elements
            categories = [li.inner_text().strip() for li in category_elements.all()]  # Extract text from each <li>
            book_details['tags'] = categories
        except:
            book_details["tags"] = []

        # Scrape Publication Date
        try:
            print("Getting book publication date...")
            date_element = page.locator(".last-updated span")
            date_text = date_element.inner_text().strip()  # Get the text and remove whitespace
            date_part = date_text.replace("LAST UPDATED ON ", "")  # Remove the prefix
            book_details['publication_date'] = date_part
        except:
            book_details["publication_date"] = None

        # Scrape Summary
        try:
            print("Getting book summary...")
            summary_element = page.locator('.book-hero__blurb')
            summary_text = summary_element.inner_text().strip()
            book_details['summary'] = summary_text
        except Exception as e:
            print(f"Error getting summary: {e}")
            book_details['summary'] = None

        # Extract Year from Publication Date and create book hash
        year = extract_year_from_date(book_details.get("publication_date"))
        book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)  # Use get

        return book_details

    except Exception as e:
        print(f"Error scraping book details: {e} Please check {url}.")
        return None


def scrape_oreilly(url: str, page):
    try:
        print(f"Opening {url}...")
        page.goto(url, timeout=10000)
        print("Waiting for elements to load...")

        page.wait_for_selector(".t-title", state="attached", timeout=10000)

        book_details = {}
        book_details["url"] = url
        book_details["site"] = "oreilly.com"

        # Scrape Title
        try:
            print("Getting book title...")
            title_element = page.locator('.t-title')  # Locate the title element
            title_text = title_element.inner_text().strip()  # Extract and clean the text
            book_details["title"] = title_text
        except Exception as e:
            print(f"Failed to get book at {url}. Check link.")
            return

        # Scrape Authors
        try:
            print("Getting book author(s)...")
            author_elements = page.locator('.author-name').all()
            author_names = set()  # Use a set to store unique author names

            for author_element in author_elements:
                author_name = author_element.inner_text().strip()
                author_names.add(author_name)

            book_details['authors'] = list(author_names)  # Convert the set back to a list
        except Exception as e:
            print(f"Error getting authors: {e}")
            book_details["authors"] = None

            # No isbn10
            book_details["isbn10"] = None

            # Scrape isbn13
            isbn13_element = page.locator('.t-isbn')
            isbn13_value = isbn13_element.inner_text().strip().replace("ISBN: ", )
            book_details["isbn13"] = isbn13_value

            # No Book Tags
            book_details["tags"] = []

        # Scrape Publication Date
        try:
            print("Getting book publication date...")
            date_element = page.locator(".t-release-date")
            date_text = date_element.inner_text().strip().replace("Released ", "")  # Get the text and remove whitespace
            book_details['publication_date'] = date_text
        except:
            book_details["publication_date"] = None

        # Scrape Summary
        try:
            print("Getting book summary...")
            summary_elements = page.locator('.content span div p')
            all_p_text = ""

            for p_element in summary_elements.all():
                all_p_text += p_element.inner_text().strip() + " "  # Add text and a space
            book_details['summary'] = all_p_text
        except Exception as e:
            print(f"Error getting summary: {e}")
            book_details['summary'] = None

        # Extract Year from Publication Date and create book hash
        year = extract_year_from_date(book_details.get("publication_date"))
        book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)  # Use get

        return book_details

    except Exception as e:
        print(f"Error scraping book details: {e} Please check {url}.")
        return None
