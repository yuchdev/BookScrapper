import argparse
import asyncio
import csv
import logging
import sys
import time

from playwright.async_api import async_playwright, Browser

from .deduplicate import leanpub_prescrape_deduplicate, amazon_prescrape_deduplicate

from .book_utils import print_log, check_csv_write_permission
from .scrape_details import get_leanpub_book_details, get_html_book_details
from .database import save_books_to_mongodb, get_mongo_collection, \
	close_mongo_connection
from .parameters import SEARCH_QUERIES, SITES_TO_SCRAPE, HEADLESS_BROWSER, site_constants
from .search_utils import get_search_results_via_playwright, get_leanpub_search_results_via_api

module_logger = logging.getLogger(__name__)


def save_books_to_csv(books: list[dict], filename="scraped_books.csv") -> None:
	"""
	Save a list of book dictionaries to a CSV file.

	This function automatically determines the CSV column headers by collecting all unique keys
	from the provided list of book dictionaries. It writes the data to the specified CSV file,
	handling any errors during the write process and logging relevant information.

	Args:
			books (list[dict]): A list of dictionaries, each representing a book's data.
			filename (str, optional): The filename for the output CSV file. Defaults to "scraped_books.csv".

	Returns:
			None

	Logs:
			- Info logs for start and successful completion of saving.
			- Error logs for issues during writing individual rows or file I/O errors.
			- Critical logs for unexpected exceptions.
	"""
	if not books:
		module_logger.info(f"No book data to save to {filename}.")
		return
	try:
		# Collect all unique fieldnames from all books
		fieldnames = set()
		for book in books:
			if book:
				fieldnames.update(book.keys())
		fieldnames = sorted(list(fieldnames))  # Sort for consistent column order

		module_logger.info(f"Saving scraped books to CSV: {filename}")
		print_log(f"Saving {len(books)} books to {filename}...", "info")

		with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
			writer = csv.DictWriter(csvfile, fieldnames=fieldnames, restval="")
			writer.writeheader()
			for book in books:
				try:
					writer.writerow(book)
				except ValueError as ve:
					module_logger.error(f"Error writing row for book {book.get('title', 'Unknown Title')} to CSV: {ve}")
				except Exception as e:
					module_logger.error(
						f"Unexpected error writing book {book.get('title', 'Unknown Title')} to CSV: {e}",
						exc_info=True)
		print_log(f"Books successfully saved to {filename}.", "success")
		module_logger.info(f"Books successfully saved to {filename}.")
	except IOError as e:
		module_logger.error(f"I/O error saving books to CSV {filename}: {e}")
		print_log(f"Error saving books to {filename}: {e}", "error")
	except Exception as e:
		module_logger.critical(f"An unexpected error occurred while saving books to CSV {filename}: {e}", exc_info=True)
		print_log(f"Critical Error saving books to {filename}. Check log file.", "error")


def save_failed_urls_to_csv(failed_urls: list[dict], filename="failed_urls.csv") -> None:
	"""
	Saves a list of dictionaries with failed URLs and their errors to a CSV file.
	Each dictionary should contain 'url', 'site', and 'error'.

	Args:
			failed_urls (list[dict]): A list of dictionaries, each containing the following keys:
					- 'url': The URL that failed to scrape.
					- 'site': The site from which the URL was scraped.
					- 'error': The error message associated with the failure.

	Returns:
			None
			:param failed_urls:
			:param filename:
	"""
	if not failed_urls:
		module_logger.info(f"No failed URLs to save to {filename}.")
		return

	try:
		fieldnames = ['url', 'site', 'error']  # Explicit fieldnames
		module_logger.info(f"Saving failed URLs to CSV: {filename}")
		print_log(f"Saving {len(failed_urls)} failed URLs to {filename}...", "info")

		with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
			writer = csv.DictWriter(csvfile, fieldnames=fieldnames, restval="")
			writer.writeheader()
			for item in failed_urls:
				try:
					writer.writerow(item)
				except ValueError as ve:
					module_logger.error(f"Error writing failed URL {item.get('url', 'Unknown URL')} to CSV: {ve}")
				except Exception as e:
					module_logger.error(
						f"Unexpected error writing failed URL {item.get('url', 'Unknown URL')} to CSV: {e}",
						exc_info=True)
		print_log(f"Failed URLs successfully saved to {filename}.", "success")
		module_logger.info(f"Failed URLs successfully saved to {filename}.")
	except IOError as e:
		module_logger.error(f"I/O error saving failed URLs to CSV {filename}: {e}")
		print_log(f"Error saving failed URLs to {filename}: {e}", "error")
	except Exception as e:
		module_logger.critical(f"An unexpected error occurred while saving failed URLs to CSV {filename}: {e}",
		                       exc_info=True)
		print_log(f"Critical Error saving failed URLs to {filename}. Check log file.", "error")


async def main():
	"""
	Main asynchronous function to run the book scraping application.

	This function orchestrates the entire scraping process:

	1. Parses command-line arguments for output preferences (CSV, MongoDB).
	2. Performs pre-flight checks for CSV write permissions and MongoDB connectivity.
	3. Prompts the user for output destination if not specified via arguments and
	   validates the chosen options against pre-flight checks.
	4. Iterates through predefined websites and search queries:
	   - Initiates search operations (e.g., Leanpub via API, Amazon via Playwright).
	   - Performs pre-scrape deduplication against existing data.
	   - Queues and executes detailed scraping tasks for newly identified books.
	5. Handles exceptions, including user interruption (KeyboardInterrupt).
	6. Summarizes the scraping results, including the number of books scraped,
	   failed attempts, and duplicates skipped.
	7. Saves the scraped data to the selected output destinations (CSV and/or MongoDB).
	8. Ensures proper closure of resources like MongoDB connections.
	"""
	print_log("=== Starting Application ===", "step")
	module_logger.info("Starting application.")

	start_time = time.time()

	parser = argparse.ArgumentParser(description="Find and scrape book data from various websites.")
	parser.add_argument("-c", "--output_to_csv", action="store_true", help="Enable output to CSV files.")
	parser.add_argument("-m", "--output_to_mongo", action="store_true", help="Enable output to MongoDB Atlas.")
	# Max search pages to limit Playwright searches for sites that have many pages.
	# For Leanpub (API), this limit is handled internally by its API call (page_size).
	parser.add_argument("--max_search_pages", type=int, default=3,  # Default changed to 3 for better testing
	                    help="Maximum number of search result pages to scrape per query per Playwright site.")

	args = parser.parse_args()

	# --- Pre-flight Checks for Output Destinations ---
	print_log("\n--- Running pre-flight checks for output destinations ---", "step")
	print_log("Checking CSV write permissions...")
	can_output_to_csv = check_csv_write_permission()

	print_log("Checking MongoDB connection...")
	mongo_collection = get_mongo_collection()
	can_output_to_mongo = mongo_collection is not None

	if not can_output_to_csv and not can_output_to_mongo:
		module_logger.error("No valid output destinations available. Please fix permission/MongoDB issues.")
		print_log("No valid output destinations available. Please fix permission/MongoDB issues. Exiting.", "error")
		sys.exit(1)

	output_to_csv = args.output_to_csv
	output_to_mongo = args.output_to_mongo

	if not args.output_to_csv and not args.output_to_mongo:
		print_log("No specific output destination chosen via command line arguments (-c, -m).")
		prompt_options = []
		if can_output_to_csv: prompt_options.append("(C)SV")
		if can_output_to_mongo: prompt_options.append("(M)ongoDB")
		if can_output_to_csv and can_output_to_mongo: prompt_options.append("(B)oth")

		prompt_options_str = ", ".join(prompt_options)
		prompt_options_str = prompt_options_str.replace(", (B)oth", " or (B)oth")

		while True:
			if not prompt_options:
				print_log("No output options available. Exiting.", "error")
				sys.exit(1)

			choice = input(f"Do you want to save to {prompt_options_str}, or (E)xit? ").lower().strip()

			if choice == 'c' and can_output_to_csv:
				output_to_csv = True
				output_to_mongo = False
				break
			elif choice == 'm' and can_output_to_mongo:
				output_to_mongo = True
				output_to_csv = False
				break
			elif choice == 'b' and can_output_to_csv and can_output_to_mongo:
				output_to_csv = True
				output_to_mongo = True
				break
			elif choice == 'e':
				print_log("Operation cancelled by user. Exiting.", "warning")
				sys.exit(0)
			else:
				print_log("Invalid choice or selected option is not available. Please try again.", "error")

	if output_to_csv and not can_output_to_csv:
		print_log("CSV output requested via argument but not available due to permission issues. Skipping CSV output.",
		          "warning")
		output_to_csv = False
	if output_to_mongo and not can_output_to_mongo:
		print_log(
			"MongoDB output requested via argument but not available due to connection issues. Skipping MongoDB output.",
			"warning")
		output_to_mongo = False

	if not output_to_csv and not output_to_mongo:
		print_log("\nNo valid output destinations selected or available after checks. Exiting.", "error")
		sys.exit(1)

	# --- Main Scraping Logic Starts Here ---
	print_log("\n--- Starting Online Book Search ---", "step")
	scraped_books_data = []  # List to store successfully scraped, detailed book dictionaries to save
	failed_scrape_attempts = []  # List to store book data that failed detailed scraping
	search_duplicates_skipped = 0  # To sum up search duplicates across all sites
	total_duplicates_skipped = 0  # To sum up duplicates across all sites
	unpublished_books = 0  # For Leanpub, unpublished books that are in progress
	initial_search_results = 0  # Cross-site search results counter

	try:
		# --- Iterate through SITES_TO_SCRAPE and perform search + scrape ---
		for site_name in [_.lower() for _ in SITES_TO_SCRAPE]:
			site_title = site_name.title()
			print_log(f"\nProcessing {site_title}...", "step")

			# Leanpub
			if site_name == "leanpub":
				site_initial_search_results = []
				leanpub_search_results = []
				deduplicated_leanpub_search_results = []

				for search_item in SEARCH_QUERIES:
					print_log(f"{site_title} - Searching for '{search_item}' via API...", "step")

					# 1. Get search results - Format: [{'site', 'title', 'book_id', 'slug', 'authors'}]
					site_initial_search_results += await get_leanpub_search_results_via_api(search_item)
				initial_search_results += len(site_initial_search_results)

				# 2. Pre-scrape deduplication
				print_log(f"{site_title} - Deduplicating {len(site_initial_search_results)} search results...", "step")

				# Deduplicate within search results by book_id
				seen_ids = set()
				for book in site_initial_search_results:
					key_value = book.get("book_id")
					if key_value not in seen_ids:
						leanpub_search_results.append(book)
						seen_ids.add(key_value)
					else:
						search_duplicates_skipped += 1
						print_log(f'{site_title} - Duplicate book found in search results: "{book.get("title")}"',
						          "warning")

				# Deduplicate with Database Leanpub book_id and slug
				db_deduplication_tasks = []
				for book in leanpub_search_results:
					book_id = book.get("book_id")
					book_slug = book.get("slug")
					book_url = site_constants["leanpub"]["SINGLE_BOOK_API"].replace("[slug]", book_slug)
					book["book_url"] = book_url
					db_deduplication_tasks.append(asyncio.to_thread(leanpub_prescrape_deduplicate, book_id, book_slug))

				print_log(
					f"Starting concurrent deduplication checks for {len(leanpub_search_results)} Leanpub books...")
				exists_results = await asyncio.gather(*db_deduplication_tasks)
				print_log(f"Finished concurrent deduplication checks for Leanpub books.", "info")

				# 3. Process the results and build the deduplicated list
				for i, book in enumerate(leanpub_search_results):
					exists = exists_results[i]
					if not exists:
						deduplicated_leanpub_search_results.append(book)
						print_log(f"{site_title} - New book found: {book.get('title')}", "success")
					else:
						total_duplicates_skipped += 1

				print_log(f"{site_title} - Deduplication done.")

				# 4. Scrape Leanpub Books
				print_log(f"\n{site_title} - Scraping {len(deduplicated_leanpub_search_results)} potential new books.",
				          "step")

				site_scrape_tasks = []
				for book_data_to_scrape in deduplicated_leanpub_search_results:
					site_scrape_tasks.append(get_leanpub_book_details(url=book_data_to_scrape.get("book_url")))
				if site_scrape_tasks:
					current_site_scraped_results = await asyncio.gather(*site_scrape_tasks)
					for result in current_site_scraped_results:
						if result is not None:
							scraped_books_data.append(result)
						else:  # Handles the Leanpub unpublished books
							unpublished_books += 1


			# Amazon
			elif site_name == "amazon":
				site_initial_search_results = []
				amazon_search_results = []
				deduplicated_amazon_search_results = []

				async with async_playwright() as p:
					browser: Browser = await p.chromium.launch(headless=HEADLESS_BROWSER)

					for search_item in SEARCH_QUERIES:
						print_log(f"{site_title} - Searching for '{search_item}' via Playwright...", "step")

						# 1. Get search results - Format: {'site', 'title', 'asin', 'book_url'}
						site_initial_search_results += await get_search_results_via_playwright(browser, 'amazon',
						                                                                       search_item)
					initial_search_results += len(site_initial_search_results)

					# 2. Pre-scrape deduplication
					print_log(f"{site_title} - Deduplicating {len(site_initial_search_results)} search results...",
					          "step")

					# Deduplicate within search results by book_id
					seen_ids = set()
					for book in site_initial_search_results:
						key_value = book.get("asin")
						if key_value not in seen_ids:
							amazon_search_results.append(book)
							seen_ids.add(key_value)
						else:
							search_duplicates_skipped += 1
							print_log(f'{site_title} - Duplicate book found in search results: "{book.get("title")}"',
							          "warning")

					# Deduplicate with Database Amazon asin
					db_deduplication_tasks = []
					for book in amazon_search_results:
						asin = book.get("asin")
						db_deduplication_tasks.append(
							asyncio.to_thread(amazon_prescrape_deduplicate, asin))

					print_log(
						f"Starting concurrent deduplication checks for {len(amazon_search_results)} {site_title} books...")
					exists_results = await asyncio.gather(*db_deduplication_tasks)
					print_log(f"Finished concurrent deduplication checks for {site_title} books.")

					# 3. Process the results and build the deduplicated list
					for i, book in enumerate(amazon_search_results):
						exists = exists_results[i]
						if not exists:
							deduplicated_amazon_search_results.append(book)
							print_log(f"{site_title} - New book found: {book.get('title')}", "success")
						else:
							total_duplicates_skipped += 1

					print_log(f"{site_title} - Deduplication done.")

					# 4. Scrape Amazon Books
					print_log(
						f"\n{site_title} - Scraping {len(deduplicated_amazon_search_results)} potential new books.",
						"step")

					site_scrape_tasks = []
					for book_data_to_scrape in deduplicated_amazon_search_results:
						site_scrape_tasks.append(get_html_book_details(book=book_data_to_scrape, browser=browser))
					if site_scrape_tasks:
						current_site_scraped_results = await asyncio.gather(*site_scrape_tasks)
						for result in current_site_scraped_results:
							if result is not None:
								scraped_books_data.append(result)
							else:  # Handles the Leanpub unpublished books
								unpublished_books += 1


			# Packtpub
			elif site_name == "packtpub":
				site_initial_search_results = []
				packtpub_search_results = []
				deduplicated_packtpub_search_results = []

				async with async_playwright() as p:
					browser: Browser = await p.chromium.launch(headless=HEADLESS_BROWSER)

					for search_item in SEARCH_QUERIES:
						print_log(f"{site_title} - Searching for '{search_item}' via Playwright...", "step")

						# 1. Get search results - Format: {'site', 'title', 'asin', 'book_url'}
						site_initial_search_results += await get_search_results_via_playwright(browser, 'amazon',
						                                                                       search_item)
					initial_search_results += len(site_initial_search_results)

					# 2. Pre-scrape deduplication
					print_log(f"{site_title} - Deduplicating {len(site_initial_search_results)} search results...",
					          "step")

					# Deduplicate within search results by book_id
					seen_ids = set()
					for book in site_initial_search_results:
						key_value = book.get("asin")
						if key_value not in seen_ids:
							amazon_search_results.append(book)
							seen_ids.add(key_value)
						else:
							search_duplicates_skipped += 1
							print_log(f'{site_title} - Duplicate book found in search results: "{book.get("title")}"',
							          "warning")

					# Deduplicate with Database Amazon asin
					db_deduplication_tasks = []
					for book in amazon_search_results:
						asin = book.get("asin")
						db_deduplication_tasks.append(
							asyncio.to_thread(amazon_prescrape_deduplicate, asin))

					print_log(
						f"Starting concurrent deduplication checks for {len(amazon_search_results)} {site_title} books...")
					exists_results = await asyncio.gather(*db_deduplication_tasks)
					print_log(f"Finished concurrent deduplication checks for {site_title} books.")

					# 3. Process the results and build the deduplicated list
					for i, book in enumerate(amazon_search_results):
						exists = exists_results[i]
						if not exists:
							deduplicated_amazon_search_results.append(book)
							print_log(f"{site_title} - New book found: {book.get('title')}", "success")
						else:
							total_duplicates_skipped += 1

					print_log(f"{site_title} - Deduplication done.")

					# 4. Scrape Amazon Books
					print_log(
						f"\n{site_title} - Scraping {len(deduplicated_amazon_search_results)} potential new books.",
						"step")

					site_scrape_tasks = []
					for book_data_to_scrape in deduplicated_amazon_search_results:
						site_scrape_tasks.append(get_html_book_details(book=book_data_to_scrape, browser=browser))
					if site_scrape_tasks:
						current_site_scraped_results = await asyncio.gather(*site_scrape_tasks)
						for result in current_site_scraped_results:
							if result is not None:
								scraped_books_data.append(result)
							else:  # Handles the Leanpub unpublished books
								unpublished_books += 1


	#
	# for original_book_data, result in zip(books_from_search, current_site_scraped_results):
	# 	if isinstance(result, dict):
	# 		scraped_books_data.append(result)
	# 		print_log(
	# 			f"Successfully scraped details for: {result.get('title')} from {site_name}",
	# 			"success")
	# 	elif isinstance(result, Exception):
	# 		failed_scrape_attempts.append({
	# 			"url": original_book_data.get("url", "N/A"),
	# 			"site": original_book_data.get("site", "N/A"),
	# 			"title": original_book_data.get("title", "N/A"),
	# 			"error": str(result)
	# 		})
	# 		print_log(
	# 			f"Failed to scrape details for {original_book_data.get('url', 'N/A')} from {site_name}: {str(result)}",
	# 			"error")
	# 	else:
	# 		failed_scrape_attempts.append({
	# 			"url": original_book_data.get("url", "N/A"),
	# 			"site": original_book_data.get("site", "N/A"),
	# 			"title": original_book_data.get("title", "N/A"),
	# 			"error": f"Detailed scrape returned unexpected type: {type(result)} - {str(result)}"
	# 		})
	# 		print_log(
	# 			f"Failed to scrape details for {original_book_data.get('url', 'N/A')} from {site_name}: Unexpected result type.",
	# 			"error")

	# exit(0)

	# Packtpub
	# Get search results - Format: {'site', 'title', '', 'book_url'}
	# Pre-scrape deduplication
	# Format: {'site', 'title', 'asin', 'book_url'}

	# O'Reilly
	# Get search results - Format: {'site', 'title', '', 'book_url'}
	# Pre-scrape deduplication
	# Format: {'site', 'title', 'asin', 'book_url'}

	# --- Deduplicate Cross-Site using ISBN / Fuzzy search / Hash ---

	# batch_size = 10
	# try:
	# 	async with async_playwright() as p:
	# 		browser = await p.chromium.launch(headless=HEADLESS_BROWSER)
	# 		print_log("Playwright browser launched successfully.")
	# 		all_urls = []
	# 		books = []
	#
	# 		for i in range(0, site_constants['amazon']['SEARCH_MAXIMUM_PAGES'], batch_size):
	# 			batch_urls = all_urls[i:i + batch_size]
	# 			print_log(
	# 				f"Starting batch {i // batch_size + 1} of {len(all_urls) // batch_size + (1 if len(all_urls) % batch_size else 0)}",
	# 				"info")
	#
	# 			tasks = []
	# 			for url in batch_urls:
	# 				site = identify_website(url)
	# 				tasks.append(scrape_book(url, browser, site))
	#
	# 			results = await asyncio.gather(*tasks)
	#
	# 			for index, result in enumerate(results):
	# 				if result:
	# 					books.append(result)
	# 				else:
	# 					failed_urls.append(batch_urls[index])
	# 					logger.warning(f"Failed to scrape: {batch_urls[index]}")
	#
	# 			if i + batch_size < total_urls:
	# 				print_log("Pausing between batches...", "info")
	# 				await asyncio.sleep(random.uniform(3, 5))

	# except Exception as e:
	# 	print_log(
	# 		f"Failed to launch Playwright browser: {e}. Playwright-based sites will be skipped.",
	# 		"critical")
	# 	module_logger.critical(f"Failed to launch Playwright browser: {e}", exc_info=True)
	# 	# Remove Playwright sites from SITES_TO_SCRAPE if browser launch fails
	# 	SITES_TO_SCRAPE[:] = [site for site in SITES_TO_SCRAPE if
	# 	                      site.lower() not in ["amazon", "packtpub", "oreilly"]]
	# if not SITES_TO_SCRAPE:  # If no sites left to scrape
	#     print_log("No sites left to scrape after browser launch failure. Exiting.", "error")
	#     sys.exit(1)

	# print_log(f"{site_name.title()} - Searching for '{search_item}' using Playwright...", "info")
	# current_search_results = await get_search_results_via_playwright(
	# 	browser=browser,
	# 	site_name=site_name,
	# 	query=search_item,
	# )

	# Compile all potential books found on all sites per search query
	# site_books_from_search.extend(current_search_results)
	# print_log(f"Found {len(books_from_search)} potential new books.", "success")
	# module_logger.info(f"Found {len(books_from_search)} potential new books.")

	# --- Scrape books from different sites ---
	# site_scrape_tasks = []
	# print_log(f"\n--- Scraping {len(books_from_search)} Book Data ---", "step")

	# async with async_playwright() as p:
	# 	browser = await p.chromium.launch(headless=HEADLESS_BROWSER)

	# for book_data_to_scrape in books_from_search:
	# 	if book_data_to_scrape['site'].lower() == "leanpub":
	# 		site_scrape_tasks.append(get_leanpub_book_details(url=book_data_to_scrape.get("book_url")))
	# elif book_data_to_scrape['site'].lower() == "amazon":
	# 	site_scrape_tasks.append(get_html_book_details(
	# 		url=book_data_to_scrape.get("book_url"),
	# 		browser=browser,
	# 		site='amazon'))

	# else:
	# 	# Other sites use Playwright for detailed scraping
	# 	if browser:  # Ensure browser is available
	# 		site_scrape_tasks.append(
	# 			scrape_book(url=book_data_to_scrape.get("book_url"), browser=browser,
	# 			            site=book_data_to_scrape.get("site")))
	# 	else:
	# 		print_log(
	# 			f"Skipping detailed scrape for {book_data_to_scrape.get('title', 'Unknown')} from {site_name} as Playwright browser is not available.",
	# 			"warning")

	# Run detailed scraping tasks for the current site concurrently
	# if site_scrape_tasks:
	# 	current_site_scraped_results = await asyncio.gather(*site_scrape_tasks, return_exceptions=True)

	# Process results from detailed scraping for the current site
	# for original_book_data, result in zip(books_from_search, current_site_scraped_results):
	# 	if isinstance(result, dict):
	# 		scraped_books_data.append(result)
	# 		print_log(
	# 			f"Successfully scraped details for: {result.get('title', 'Unknown Title')} from {site_name}",
	# 			"info")
	# 	elif isinstance(result, Exception):
	# 		failed_scrape_attempts.append({
	# 			"url": original_book_data.get("url", "N/A"),
	# 			"site": original_book_data.get("site", "N/A"),
	# 			"title": original_book_data.get("title", "N/A"),
	# 			"error": str(result)
	# 		})
	# 		print_log(
	# 			f"Failed to scrape details for {original_book_data.get('url', 'N/A')} from {site_name}: {str(result)}",
	# 			"error")
	# 	else:
	# 		failed_scrape_attempts.append({
	# 			"url": original_book_data.get("url", "N/A"),
	# 			"site": original_book_data.get("site", "N/A"),
	# 			"title": original_book_data.get("title", "N/A"),
	# 			"error": f"Detailed scrape returned unexpected type: {type(result)} - {str(result)}"
	# 		})
	# 		print_log(
	# 			f"Failed to scrape details for {original_book_data.get('url', 'N/A')} from {site_name}: Unexpected result type.",
	# 			"error")
	# else:
	# 	print_log(f"No new books identified for detailed scraping on {site_name}.", "info")

	# --- Post-Scrape cross-site deduplication ---

	# --- Save to CSV/MongoDB ---

	# --- Deduplicate Cross-Site using ISBN / Fuzzy search / Hash ---
	# new_books_for_detailed_scrape = await check_for_new_books_before_scrape(site_books_from_search)
	# new_books_for_detailed_scrape = books_from_search

	# Calculate duplicates skipped for this site
	# site_duplicates_skipped = len(site_books_from_search) - len(new_books_for_detailed_scrape)
	# total_duplicates_skipped += site_duplicates_skipped

	# print_log(
	# 	f"{site_name.title()} - Identified {len(new_books_for_detailed_scrape)} new book{'s' if len(new_books_for_detailed_scrape) != 1 else ''} for detailed scraping (skipped {site_duplicates_skipped} duplicates).",
	# 	"info")

	except KeyboardInterrupt:
		print_log("Scraping interrupted by user.", "warning")
		module_logger.warning("Application interrupted by user.")
	except Exception as e:
		module_logger.critical(f"An unhandled error occurred in main execution: {e}", exc_info=True)
		print_log(f"Critical error in main execution. Check logs: {e}", "error")

	# --- End of Site Iteration ---

	# Close Playwright browser if it was launched
	# if browser:
	# 	await browser.close()
	# 	await p_context.__aexit__(None, None, None)  # Properly close Playwright context
	# 	print_log("Playwright browser closed.", "info")

	total_time = time.time() - start_time
	print_log(f"\n--- Scraping Process Summary ---", "step")
	print_log(f"Total scraping process completed in {total_time:.2f} seconds.")
	print_log(f"{initial_search_results} book{'s' if initial_search_results != 1 else ''} found in initial search.")
	print_log(f"{len(scraped_books_data)} new book{'s' if len(scraped_books_data) != 1 else ''} scraped.")
	print_log(f"{search_duplicates_skipped} search duplicate{'s' if search_duplicates_skipped != 1 else ''} found.")
	print_log(f"{total_duplicates_skipped} book{'s' if total_duplicates_skipped != 1 else ''} already in the database.")
	print_log(f"{unpublished_books} unpublished book{'s' if unpublished_books != 1 else ''} skipped.")
	print_log(
		f"{len(failed_scrape_attempts)} URL{'s' if len(failed_scrape_attempts) != 1 else ''} failed during detailed scrape.",
		"warning" if len(failed_scrape_attempts) > 0 else "info")

	# --- Output Saving ---
	print_log("\n--- Output Summary ---", "step")
	if output_to_csv and can_output_to_csv:
		save_books_to_csv(scraped_books_data)
		save_failed_urls_to_csv(failed_scrape_attempts)
	elif output_to_csv and not can_output_to_csv:
		print_log("CSV output was requested but not possible due to permissions.", "error")
	else:
		print_log("CSV output not requested.", "info")

	if output_to_mongo and can_output_to_mongo:
		if scraped_books_data:
			print_log("Saving newly scraped books to MongoDB database...")
			save_books_to_mongodb(scraped_books_data, mongo_collection)
		else:
			print_log("No new books to save to MongoDB database.")
	elif output_to_mongo and not can_output_to_mongo:
		print_log("MongoDB output not possible. Check connection string/permissions.", "error")
	else:
		print_log("MongoDB output not requested.", "info")

	# finally:
	# 	# Ensure Playwright browser and context are closed even if other errors occur
	# 	if browser and not browser.is_closed():
	# 		await browser.close()
	# 	if p_context:
	# 		await p_context.__aexit__(None, None, None)
	# 		print_log("Playwright browser closed in finally block.", "info")

	if can_output_to_mongo:
		close_mongo_connection()

	print_log("\nApplication finished.", "step")
	module_logger.info("Application finished.")


if __name__ == "__main__":
	asyncio.run(main())
