import random
import re

from fake_useragent import UserAgent
from playwright_stealth import stealth_async, stealth_sync

from .book_utils import hash_book, extract_year_from_date
from .site_constants import amazon_constants


def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15; rv:109.0) Gecko/20100101 Firefox/111.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0",
        # Add more realistic User-Agents
    ]
    return random.choice(user_agents)


def get_site(url: str) -> str:
    site_pattern = r"(?://(.+?)/)"
    try:
        match = re.findall(site_pattern, url)
        if match:
            return match[0]
        else:
            return ''
    except Exception as e:
        site = ''
        print(f"Error occurred while parsing URL: {e}")


def scrape_packtpub(url: str, page):
    try:
        print(f"Opening {url}...")
        page.goto(url, timeout=10000)
        print("Waiting for elements to load...")

        page.wait_for_selector("h1.product-title", state="attached", timeout=3000)

        book_details = {"url": url, "site": "packtpub.com"}

        # Scrape Title
        try:
            print("Getting book title...")
            book_details["title"] = page.locator("h1.product-title").inner_text().strip()
        except Exception as e:
            print(f"Failed to get book at {url}. Check link.")
            return

        # Scrape Authors
        try:
            print("Getting book author(s)...")
            page.wait_for_selector('.authors .authors-dark', timeout=10000)  # Wait for authors

            author_elements = page.locator('.authors .authors-dark').all()
            author_names = set()  # Use a set to store unique author names

            for author_element in author_elements:
                author_name = author_element.inner_text().strip()
                author_names.add(author_name)

            book_details['authors'] = list(author_names)  # Convert the set back to a list
        except Exception as e:
            print(f"Error getting authors: {e}")
            book_details["authors"] = None

        # Scrape isbn13
        try:
            print("Getting book isbn13...")
            isbn_parent = page.get_by_text("ISBN-13 :").locator("..")  # ".." goes to the parent element
            isbn_value_element = isbn_parent.locator("*").nth(1)  # * selects all children, nth(1) gets the second one
            book_details['isbn13'] = isbn_value_element.inner_text().strip()
        except:
            book_details["isbn13"] = None

        # Scrape Book Tags
        try:
            print("Getting book tags...")
            tag_parent = page.get_by_text("Category :").locator("..")  # ".." goes to the parent element
            tag_value_element = tag_parent.locator("*").nth(1)  # * selects all children, nth(1) gets the second one
            book_details['tags'] = tag_value_element.inner_text().strip()
        except:
            book_details["tags"] = []

        # Scrape Publication Date
        try:
            print("Getting book publication date...")
            pub_date_parent = page.get_by_text("Publication date :").locator("..")  # ".." goes to the parent element
            pub_date_value_element = pub_date_parent.locator("*").nth(
                1)  # * selects all children, nth(1) gets the second one
            book_details['publication_date'] = pub_date_value_element.inner_text().strip()
        except:
            book_details["publication_date"] = None

        # Scrape Summary
        try:
            print("Getting book summary...")
            description_element = page.locator('.product-book-content-details .content-text').nth(
                1)  # Select the 2nd .content-text (description)
            book_details['description'] = description_element.inner_text().strip()
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


def scrape_amazon(url, browser):
    retries = 3
    for attempt in range(retries):
        try:
            page = browser.new_page()
            ua = UserAgent(platforms='desktop')
            chosen_user_agent = ua.random
            # print(f"Using User-Agent: {chosen_user_agent}")
            stealth_sync(page)  # Use stealth_sync
            page.set_extra_http_headers({"User-Agent": chosen_user_agent})

            print(f"Opening {url}...")
            try:
                page.goto(url, timeout=30000)
            except TimeoutError:
                print(f"Timeout navigating to {url}")
                return None

            # Waiting for page to load
            print("Waiting for elements to load...")

            book_details = {"url": url, "site": "amazon.com"}

            # Scrape Title
            try:
                print("Getting book title...")
                page.wait_for_selector(amazon_constants.TITLE, state="attached", timeout=10000)
                book_details["title"] = page.locator(amazon_constants.TITLE).inner_text().strip()
            except TimeoutError as e:
                print(f"Failed to get book at {url}. Check link.")
                return

            # Scrape Authors
            try:
                print("Getting book author(s)...")
                page.wait_for_selector(amazon_constants.AUTHORS, timeout=10000)
                book_details["authors"] = [
                    author.inner_text().strip() for author in page.locator(amazon_constants.AUTHORS).all()
                ]
            except:
                book_details["authors"] = []

            # Scrape isbn10
            try:
                print("Getting book isbn10...")
                page.wait_for_selector(amazon_constants.ISBN10, timeout=10000)
                book_details["isbn10"] = page.locator(
                    amazon_constants.ISBN10).inner_text().strip()
            except:
                book_details["isbn10"] = None

            # Scrape isbn13
            try:
                print("Getting book isbn10...")
                page.wait_for_selector(amazon_constants.ISBN13, timeout=10000)
                book_details["isbn13"] = page.locator(
                    amazon_constants.ISBN13).inner_text().strip()
            except:
                book_details["isbn13"] = None

            # Scrape Book Tags
            try:
                print("Getting book tags...")

                book_details["tags"] = [
                    tag.inner_text().replace("(Books)", "").strip() for tag in
                    page.locator("#detailBulletsWrapper_feature_div ul li ul li a").all()
                ]
            except:
                book_details["tags"] = []

            # Scrape Publication Date
            try:
                print("Getting book publication date...")
                page.locator("a:has-text('Next slide of product details')").click()
                page.wait_for_selector("#rpi-attribute-book_details-publication_date", state="attached")
                book_details["publication_date"] = page.locator(
                    "div#rpi-attribute-book_details-publication_date div.rpi-attribute-value span").inner_text().strip()
            except:
                book_details["publication_date"] = None

            # Scrape Description
            try:
                print("Getting book summary...")

                # Integrated description logic:
                full_description = page.locator("#bookDescription_feature_div .a-expander-content").inner_text().strip()
                if full_description:
                    book_details["summary"] = full_description
                else:  # Check for "Read more" and click if necessary
                    read_more_link = page.locator("#bookDescription_feature_div .a-expander-prompt")
                    if read_more_link.is_visible():
                        read_more_link.click()
                        page.wait_for_selector(
                            "#bookDescription_feature_div .a-expander-content:not(.a-expander-partial-collapse-content)",
                            state="attached")
                        full_description = page.locator(
                            "#bookDescription_feature_div .a-expander-content").inner_text().strip()
                        book_details["summary"] = full_description
                    else:
                        book_details["summary"] = None  # Handle the case where there's no description

            except Exception as e:
                print(f"Error getting summary: {e}")
                book_details["summary"] = None

            year = extract_year_from_date(book_details.get("publication_date"))
            book_details["hash"] = hash_book(book_details.get("title"), book_details.get("authors"), year)  # Use get

            return book_details

        except Exception as e:
            print(f"Error scraping book details: {e} Please check {url}.")
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
