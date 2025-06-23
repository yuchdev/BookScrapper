import argparse
import asyncio
import csv
import logging
import sys
import time

from playwright.async_api import async_playwright

from .deduplicate import leanpub_prescrape_deduplicate

from .book_utils import print_log, check_csv_write_permission, hash_book, extract_year_from_date
from .scrape_details import scrape_book, get_leanpub_book_details
from .database import save_books_to_mongodb, check_book_exists_in_db, update_book_isbn, get_mongo_collection, \
	close_mongo_connection, check_amazon_asin_exists_in_db, check_for_new_books_before_scrape
from .parameters import SEARCH_QUERIES, SITES_TO_SCRAPE, SCRAPE_FILTERS, HEADLESS_BROWSER, site_constants
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
	start_time = time.time()
	module_logger.info("Application started.")

	parser = argparse.ArgumentParser(description="Find and scrape book data from various websites.")
	parser.add_argument("-c", "--output_to_csv", action="store_true", help="Enable output to CSV files.")
	parser.add_argument("-m", "--output_to_mongo", action="store_true", help="Enable output to MongoDB Atlas.")
	# Max search pages to limit Playwright searches for sites that have many pages.
	# For Leanpub (API), this limit is handled internally by its API call (page_size).
	parser.add_argument("--max_search_pages", type=int, default=3,  # Default changed to 3 for better testing
	                    help="Maximum number of search result pages to scrape per query per Playwright site.")

	args = parser.parse_args()

	# --- Pre-flight Checks for Output Destinations ---
	print_log("Running pre-flight checks for output destinations...", "info")
	print_log("Checking CSV write permissions...", "info")
	can_output_to_csv = check_csv_write_permission()

	print_log("Checking MongoDB connection...", "info")
	mongo_collection = get_mongo_collection()
	can_output_to_mongo = mongo_collection is not None

	if not can_output_to_csv and not can_output_to_mongo:
		module_logger.error("No valid output destinations available. Please fix permission/MongoDB issues.")
		print_log("No valid output destinations available. Please fix permission/MongoDB issues. Exiting.", "error")
		sys.exit(1)

	output_to_csv = args.output_to_csv
	output_to_mongo = args.output_to_mongo

	if not args.output_to_csv and not args.output_to_mongo:
		print_log("No specific output destination chosen via command line arguments (-c, -m).", "info")
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
				print_log("Operation cancelled by user. Exiting.", "info")
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
	scraped_books_data = []  # List to store successfully scraped, detailed book dictionaries to save
	failed_scrape_attempts = []  # List to store book data that failed detailed scraping
	total_duplicates_skipped = 0  # To sum up duplicates across all sites
	books_from_search = []

	try:
		# --- Iterate through SITES_TO_SCRAPE and perform search + scrape ---
		for site_name in SITES_TO_SCRAPE:
			print_log(f"\n--- Processing {site_name.title()} ---", "step")

			for search_item in SEARCH_QUERIES:
				current_search_results = []
				# Leanpub-Specific
				if site_name.lower() == "leanpub":
					print_log(f"Leanpub - Searching for '{search_item}' via API...", "info")

					# Get search results - Format: [{'site', 'title', 'book_id', 'slug', 'authors'}]
					current_search_results = await get_leanpub_search_results_via_api(search_item)

					# Pre-scrape deduplication
					print_log("Leanpub - Deduplicating search results...")
					for book in current_search_results:
						book_title = book.get("title")
						book_id = book.get("book_id")
						book_slug = book.get("slug")
						book_url = site_constants["leanpub"]["SINGLE_BOOK_API"].replace("[slug]", book_slug)
						book["book_url"] = book_url
						exists = await asyncio.to_thread(leanpub_prescrape_deduplicate, book_id, book_slug)

						if not exists:
							# Format: {'site', 'title', 'book_id', 'slug', 'authors', 'book_url'}
							books_from_search.append(book)
							print_log(f"{site_name.title()} - New book found: {book_title}", "success")
						else:
							total_duplicates_skipped += 1
							print_log(f"{site_name.title()} - Book already in database: {book_title}", 'warning')

				elif site_name.lower() == "amazon":
					# Amazon
					batch_size = 10
					try:
						async with async_playwright() as p:
							browser = await p.chromium.launch(headless=HEADLESS_BROWSER)
							print_log("Playwright browser launched successfully.")
							books = []

							for i in range(0, site_constants['amazon']['SEARCH_MAXIMUM_PAGES'], batch_size):
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





					except Exception as e:
						print_log(
							f"Failed to launch Playwright browser: {e}. Playwright-based sites will be skipped.",
							"critical")
						module_logger.critical(f"Failed to launch Playwright browser: {e}", exc_info=True)
						# Remove Playwright sites from SITES_TO_SCRAPE if browser launch fails
						SITES_TO_SCRAPE[:] = [site for site in SITES_TO_SCRAPE if
						                      site.lower() not in ["amazon", "packtpub", "oreilly"]]
					# if not SITES_TO_SCRAPE:  # If no sites left to scrape
					#     print_log("No sites left to scrape after browser launch failure. Exiting.", "error")
					#     sys.exit(1)

					print_log(f"{site_name.title()} - Searching for '{search_item}' using Playwright...", "info")
					current_search_results = await get_search_results_via_playwright(
						browser=browser,
						site_name=site_name,
						query=search_item,
					)

				# Compile all potential books found on all sites per search query
				# site_books_from_search.extend(current_search_results)
				print_log(f"Found {len(current_search_results)} potential new books for '{search_item}'.", "success")
				module_logger.info(f"Found {len(current_search_results)} potential new books for '{search_item}'.")

		# --- Deduplicate Cross-Site using ISBN / Fuzzy search / Hash ---
		# new_books_for_detailed_scrape = await check_for_new_books_before_scrape(site_books_from_search)
		new_books_for_detailed_scrape = books_from_search

		# Calculate duplicates skipped for this site
		# site_duplicates_skipped = len(site_books_from_search) - len(new_books_for_detailed_scrape)
		# total_duplicates_skipped += site_duplicates_skipped

		# print_log(
		# 	f"{site_name.title()} - Identified {len(new_books_for_detailed_scrape)} new book{'s' if len(new_books_for_detailed_scrape) != 1 else ''} for detailed scraping (skipped {site_duplicates_skipped} duplicates).",
		# 	"info")

		# --- Queue Detailed Scraping Tasks for current site ---
		site_scrape_tasks = []
		for book_data_to_scrape in new_books_for_detailed_scrape:
			if book_data_to_scrape['site'].lower() == "leanpub":
				print_log(f"--- Scraping {len(book_data_to_scrape)} Book Data ---", "step")
				# Scraping Leanpub details via httpx API
				site_scrape_tasks.append(get_leanpub_book_details(url=book_data_to_scrape.get("book_url")))
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
		if site_scrape_tasks:
			current_site_scraped_results = await asyncio.gather(*site_scrape_tasks, return_exceptions=True)

			# Process results from detailed scraping for the current site
			for original_book_data, result in zip(new_books_for_detailed_scrape, current_site_scraped_results):
				if isinstance(result, dict):
					scraped_books_data.append(result)
					print_log(
						f"Successfully scraped details for: {result.get('title', 'Unknown Title')} from {site_name}",
						"info")
				elif isinstance(result, Exception):
					failed_scrape_attempts.append({
						"url": original_book_data.get("url", "N/A"),
						"site": original_book_data.get("site", "N/A"),
						"title": original_book_data.get("title", "N/A"),
						"error": str(result)
					})
					print_log(
						f"Failed to scrape details for {original_book_data.get('url', 'N/A')} from {site_name}: {str(result)}",
						"error")
				else:
					failed_scrape_attempts.append({
						"url": original_book_data.get("url", "N/A"),
						"site": original_book_data.get("site", "N/A"),
						"title": original_book_data.get("title", "N/A"),
						"error": f"Detailed scrape returned unexpected type: {type(result)} - {str(result)}"
					})
					print_log(
						f"Failed to scrape details for {original_book_data.get('url', 'N/A')} from {site_name}: Unexpected result type.",
						"error")
		else:
			print_log(f"No new books identified for detailed scraping on {site_name}.", "info")


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
	print_log(f"{len(scraped_books_data)} new book{'s' if len(scraped_books_data) != 1 else ''} scraped.")
	print_log(f"{len(failed_scrape_attempts)} URLs failed during detailed scrape.",
	          "warning" if len(failed_scrape_attempts) > 0 else "info")
	print_log(f"{total_duplicates_skipped} books already in the database and skipped.")

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
