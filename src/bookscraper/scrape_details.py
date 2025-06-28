import asyncio
import json
import random
import logging
import re
from datetime import datetime
from html import unescape
from urllib.parse import urljoin

import httpx

from .book_utils import hash_book, extract_year_from_date, print_log

from .parameters import USER_AGENTS, site_constants, HEADLESS_BROWSER
from .database import check_book_exists_in_db  # Import the new duplicate check function
from pymongo.collection import Collection  # For type hinting the collection object
from playwright.async_api import Browser, TimeoutError, async_playwright, Page

# Get a logger instance specifically for this module
module_logger = logging.getLogger('scrape_details')


async def route_handler(route):
	request = route.request
	# Allow document (HTML page) requests to go through.
	# Block other resource types (images, fonts, stylesheets, etc.) to speed up scraping.
	if request.resource_type == "document":
		await route.continue_()
	else:
		await route.abort()


async def get_leanpub_book_details(url: str):
	"""
	Fetches detailed information for a single Leanpub book from the provided JSON structure.

	Args:
		url (str): The API endpoint of the book (e.g., "https://leanpub.com/api/v1/cache/books/quickguidetodatasciencewithpython.json").

	Returns:
		dict: A dictionary containing extracted book details, or None if an error occurs.
	"""
	# In a real application, you would make an HTTP request here:
	params = {"include": "accepted_authors"}  # Keep this if 'included' authors are still needed from API

	try:
		async with httpx.AsyncClient() as client:
			response = await client.get(url, params=params, timeout=30.0)
			response.raise_for_status()
			response_data = response.json()

			book_data = response_data.get("data")
			if not book_data:
				print(f"No 'data' found in response for book slug: {url}")
				return None

			attributes = book_data.get("attributes", {})
			relationships = book_data.get("relationships", {})
			included = response_data.get("included", [])  # Relevant for authors
			description = unescape(attributes.get("about_the_book"))
			description = re.sub(r'</p>', '\n\n', description, flags=re.IGNORECASE)
			description = re.sub(r'</li>', '\n', description, flags=re.IGNORECASE)
			description = re.sub(r'<[^>]*>', '', description)
			description = re.sub(r'\n\n+', '\n\n', description).strip()
			description = re.sub(r' +', ' ', description)

			extracted_details = {
				"site": "leanpub",
				"title": attributes.get("title"),
				"book_id": book_data.get("id"),
				"authors": [],
				"description": description,
				"categories": [],
				"publication_date": None,
				"hash": ""}

			# Extract Last published at
			publication_date_str = attributes.get("last_published_at")
			if publication_date_str and publication_date_str is not None:
				try:
					# 'Z' indicates UTC. datetime.fromisoformat handles '+00:00'
					dt_object = datetime.fromisoformat(publication_date_str.replace('Z', '+00:00'))
					extracted_details["publication_date"] = dt_object.strftime("%Y-%m-%d")
				except ValueError:
					print_log(f"Warning: Could not parse date string: '{publication_date_str}'", "warning")
					return None
			else:
				print_log(f"Leanpub - Unpublished book: {extracted_details['title']} - skipping.", "warning")
				module_logger.info(f"Leanpub - Unpublished book: {extracted_details['title']} - skipping.")
				return None

			# Extract authors
			author_lookup = {}
			for item in included:
				# Ensure the 'type' matches 'Author' now, not 'SimpleAuthor'
				if item.get("type") == "Author":
					author_id = item.get("id")
					author_name = item.get("attributes", {}).get("name")
					if author_id and author_name:
						author_lookup[author_id] = author_name

			accepted_authors_data = relationships.get("accepted_authors", {}).get("data", [])
			for author_rel in accepted_authors_data:
				author_id = author_rel.get("id")
				if author_id and author_id in author_lookup:
					extracted_details["authors"].append(author_lookup[author_id])

			# Extract Categories from data.attributes.categories
			categories_data = attributes.get("categories", [])
			for category_item in categories_data:
				category_name = category_item.get("name")
				if category_name:
					extracted_details["categories"].append(category_name)

			# Create Hash for quick alternate deduplication
			extracted_details["hash"] = hash_book(extracted_details["title"], extracted_details["authors"],
			                                      extract_year_from_date(extracted_details["publication_date"]))

			return extracted_details

	except httpx.HTTPStatusError as e:
		print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
		return None
	except httpx.RequestError as exc:
		print(f"An HTTP error occurred while requesting {exc.request.url!r}: {exc}")
		return None
	except json.JSONDecodeError:
		print_log(f"Failed to decode JSON response for url '{url}'. Response content: {response.text[:200]}...",
		          "error")
		return None
	except Exception as e:
		print(f"An unexpected error occurred for url '{url}': {e}")
		return None


async def get_html_book_details(book: dict, browser: Browser) -> dict | None:
	"""
	Scrapes book details from a given URL, handles retries, and checks for duplicates.

	Args:
		url: The URL of the book page to scrape (can be relative).
		browser: The Playwright browser instance.
		site: The identifier for the website (e.g., "amazon", "leanpub").
		mongo_collection: The MongoDB collection object for duplicate checking.

	Returns:
		A dictionary of book details on successful scrape, (None, "DUPLICATE") if already exists,
		or (None, "FAILED") on failure.
		:param book:
		:param browser:
		:param mongo_collection:
		:param site:
		:param url:
		:param page:
	"""

	book_url = book.get("book_url")
	book_title = book.get("title")
	site = book.get("site")

	retries = 3
	for attempt in range(1, retries + 1):
		# print(f"Trying attempt {attempt}...")

		try:
			page: Page = await browser.new_page()
			user_agent = random.choice(USER_AGENTS)
			await page.set_extra_http_headers({"User-Agent": user_agent})
			await page.route("**/*", route_handler)
			# print_log(f'Navigating to "{book_title}" for detailed scraping.')
			module_logger.info(f'Navigating to "{book_title}" for detailed scraping.')
			await page.goto(book_url, wait_until="domcontentloaded", timeout=60000)

			selectors = site_constants[site]

			# Check for 404 page (if site_constants provides a 404 selector)
			if site_constants[site].get("404_PAGE_TITLE"):
				page_title = await page.title()
				if site_constants[site]["404_PAGE_TITLE"].lower() in page_title.lower():
					module_logger.warning(f"404 page detected for {book_url}. Skipping.")
					print_log(f"404 page detected for {book_url}. Skipping.", "warning")
					await page.close()
					return None

			# Authors
			authors_list = []
			# Metadata authors (e.g., for Leanpub)
			meta_author_selector_meta = selectors.get("AUTHORS_META")
			author_selector = selectors.get("AUTHORS")
			if meta_author_selector_meta:
				all_author_elements = await page.locator(meta_author_selector_meta).all()
				for author_element in all_author_elements:
					author_name = await author_element.get_attribute('content')
					if author_name:
						authors_list.append(author_name)
			# HTML Scraping alternative
			elif author_selector:
				author_elements = await page.locator(author_selector).all()
			for author_el in author_elements:
				author_name = await author_el.text_content()
				if author_name:
					authors_list.append(author_name.strip())
			if not authors_list:
				alt_author_selector = selectors.get("AUTHORS_ALT")
				if alt_author_selector:
					author_elements = await page.locator(alt_author_selector).all()
					for author_el in author_elements:
						author_name = await author_el.text_content()
						if author_name:
							authors_list.append(author_name.strip())
			book["authors"] = authors_list if authors_list else []

			# Publication Date
			try:
				# use Metadata (e.g., for Leanpub)
				meta_publication_date_selector = selectors.get("PUBLICATION_DATE_META")
				if meta_publication_date_selector:
					pub_date_text = await page.locator(meta_publication_date_selector).get_attribute('content',
					                                                                                 timeout=10000)
					book["publication_date"] = pub_date_text.split('T')[0]
					book["publication_year"] = extract_year_from_date(book["publication_date"])
				else:
					publication_date_selector = selectors.get("PUBLICATION_DATE")
					if publication_date_selector:
						pub_date_text = await page.locator(publication_date_selector).first.text_content(timeout=10000)
						book["publication_date"] = pub_date_text.strip() if pub_date_text else None
						book["publication_year"] = extract_year_from_date(book["publication_date"])
					else:
						module_logger.warning(f"No PUBLICATION_DATE selector for {site}.")
			except Exception as e:
				module_logger.warning(f"No PUBLICATION_DATE selector for {site}: {e}.")

			# ISBN10 & ISBN13
			isbn10_selector = selectors.get("ISBN10")
			isbn13_selector = selectors.get("ISBN13")

			if isbn10_selector:
				try:
					isbn10_text = await page.locator(isbn10_selector).first.text_content(timeout=2000)
					book["isbn10"] = isbn10_text.strip() if isbn10_text else "N/A"
				except TimeoutError:
					# If a TimeoutError occurs, the element was not found within the timeout
					book["isbn10"] = "N/A"
					module_logger.info(f"ISBN10 element not found for {book_title}.")
			else:
				book["isbn10"] = "N/A"

			if isbn13_selector:
				try:
					isbn13_text = await page.locator(isbn13_selector).first.text_content(timeout=2000)
					book["isbn13"] = isbn13_text.strip() if isbn13_text else "N/A"
				except TimeoutError:
					# If a TimeoutError occurs, the element was not found within the timeout
					book["isbn13"] = "N/A"
					module_logger.info(f"ISBN13 element not found for {book_title}.")
			else:
				# If the selector itself is not defined in parameters.py
				book["isbn13"] = "N/A"

			# Amazon ASIN extraction
			# if site == "amazon":
			# 	try:
			# 		asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url)
			# 		if asin_match:
			# 			book_details["asin"] = asin_match.group(1)
			# 			module_logger.info(f"Extracted ASIN: {book_details['asin']} for {book_details['title']}.")
			# 	except Exception as e:
			# 		module_logger.warning(f"Could not extract ASIN from Amazon URL {url}: {e}")

			# Description
			description_selector = selectors.get("DESCRIPTION")
			if description_selector:
				description_element = page.locator(description_selector).first
				if description_element:
					# Check for a "Read more" link/button to expand description
					read_more_selector = selectors.get("READ_MORE_LINK")
					if read_more_selector:
						try:
							read_more_button = page.locator(read_more_selector).first
							if await read_more_button.is_visible():
								await read_more_button.click(timeout=5000)  # Click to expand
								await page.wait_for_timeout(500)  # Small wait for content to load
						except TimeoutError:
							module_logger.debug(f"No 'Read more' button found or clickable for {book_title}.")
						except Exception as e:
							module_logger.warning(f"Error clicking 'Read more' on {book_title}: {e}")

					description_text = await description_element.text_content()
					book["description"] = description_text.strip() if description_text else None
				else:
					book["description"] = None
			else:
				module_logger.warning(f"No DESCRIPTION selector for {site}.")
				book["description"] = None

			# Generate hash
			book["hash"] = hash_book(book_title, book['authors'], book['publication_year'])

			await page.close()
			return book

		except TimeoutError as e:
			module_logger.error(f"Timeout while scraping {book_url}: {e}")
			print_log(f"Timeout scraping {book_url}. Retrying...", "error")
			break
		except Exception as e:
			print_log(f"Error navigating to {book_url}: {e}", "error")
			break
	return None
