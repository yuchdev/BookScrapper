import asyncio
import logging
import os
from typing import Tuple, Optional

from dotenv import load_dotenv
from pymongo import MongoClient, server_api
from pymongo.collection import Collection
from pymongo.errors import ServerSelectionTimeoutError, InvalidDocument, ConnectionFailure, DuplicateKeyError, \
	OperationFailure

from .book_utils import print_log

from .parameters import site_constants

module_logger = logging.getLogger(__name__)

# Global variables to hold the MongoDB client, database, and collection
_mongo_client = None
_mongo_db = None
_mongo_collection = None


def _initialize_mongodb_connection() -> Tuple[Optional[MongoClient], Optional[Collection]]:
	"""
	Initializes the MongoDB client and books collection.
	This function should only be called once when the application starts or if the connection is lost.
	Sets the global _mongo_client, _mongo_db, and _mongo_collection variables.
	"""
	global _mongo_client, _mongo_db, _mongo_collection

	# Initialize to None at the start for clear type handling
	_mongo_client = None
	_mongo_db = None
	_mongo_collection = None

	load_dotenv()
	mongodb_uri = os.environ.get("MONGODB_URI")
	tls_ca_file = os.environ.get("TLS_CA_FILE")  # CA bundle for server certificate verification
	tls_client_cert_key_file = os.environ.get("TLS_CERT_FILE")  # Client certificate/key for X.509 authentication

	if not mongodb_uri:
		module_logger.critical("MONGODB_URI not found in environment variables. Cannot connect to MongoDB.")
		# print_log("Error: MONGODB_URI not found in environment variables. Aborting MongoDB connection.", "error")
		return None, None

	# Log TLS file status before connection attempt
	if tls_ca_file:
		module_logger.info("TLS_CA_FILE set. Using explicit server CA verification.")
	else:
		module_logger.info(
			"TLS_CA_FILE not set. Proceeding without explicit server CA verification (may rely on system CAs).")

	if tls_client_cert_key_file:
		if not os.path.exists(tls_client_cert_key_file):
			module_logger.critical(
				f"MONGODB-X509 authentication specified but TLS_CERT_FILE not found: {tls_client_cert_key_file}.")
			print_log(f"Critical Error: TLS_CERT_FILE not found: {tls_client_cert_key_file}. Aborting connection.",
			          "error")
			return None, None
		module_logger.info(f"Using X.509 client certificate/key file for authentication: {tls_client_cert_key_file}")
	else:
		module_logger.info("TLS_CERT_FILE not set. X.509 authentication will not be used.")

	try:
		if tls_client_cert_key_file:
			_mongo_client = MongoClient(
				mongodb_uri,
				server_api=server_api.ServerApi('1'),
				tls=True,
				tlsCAFile=tls_ca_file,
				tlsCertificateKeyFile=tls_client_cert_key_file,
				tlsAllowInvalidCertificates=False
			)
		else:
			_mongo_client = MongoClient(
				mongodb_uri,
				server_api=server_api.ServerApi('1'),
				tlsCAFile=tls_ca_file,
				tlsAllowInvalidCertificates=False
			)

		# The ping command is used to confirm that the connection has been established.
		_mongo_client.admin.command('ping')
		# module_logger.info("Successfully connected to MongoDB Atlas!")
		# print_log("Successfully connected to MongoDB Atlas!", "info")

		_mongo_db = _mongo_client[os.environ.get("MONGODB_DB_NAME", "bookscraper_db")]
		_mongo_collection = _mongo_db[os.environ.get("MONGODB_COLLECTION_NAME", "books")]

		# Ensure a unique index on 'hash' to prevent duplicate insertions
		ensure_unique_index_on_hash(_mongo_collection)

		return _mongo_client, _mongo_collection

	except (ConnectionFailure, ServerSelectionTimeoutError) as e:
		module_logger.critical(f"Failed to connect to MongoDB Atlas: {e}")
		print_log(
			f"Critical Error: Failed to connect to MongoDB Atlas. Please check your connection string and network. Details: {e}",
			"error")
		_mongo_client = None  # Reset globals on failure
		_mongo_db = None
		_mongo_collection = None
		return None, None
	except Exception as e:
		module_logger.critical(f"An unexpected error occurred during MongoDB operation: {e}", exc_info=True)
		print_log(
			f"Critical Error: An unexpected error occurred during MongoDB operation. Please check the log file for full traceback. Details: {e}",
			"error")
		_mongo_client = None  # Reset globals on failure
		_mongo_db = None
		_mongo_collection = None
		return None, None


def get_mongo_collection() -> Collection | None:
	"""
	Returns the globally managed MongoDB collection.
	Initializes the connection if it doesn't exist.
	"""
	global _mongo_client, _mongo_db, _mongo_collection

	if _mongo_collection is None:
		try:
			# Attempt to initialize the connection if it's not already set up
			_mongo_client, _mongo_collection = _initialize_mongodb_connection()
			print_log("Connection to MongoDB Atlas successful.", "success")
			module_logger.info("Connection to MongoDB Atlas successful.")
		except Exception as e:
			print_log(f"MongoDB connection: FAILED. MongoDB output will not be available: {e}", "error")

	return _mongo_collection


def close_mongo_connection():
	"""
	Closes the global MongoDB client connection.
	"""
	global _mongo_client, _mongo_db, _mongo_collection
	if _mongo_client is not None:
		_mongo_client.close()
		_mongo_client = None
		_mongo_db = None
		_mongo_collection = None
		module_logger.info("MongoDB connection closed.")


def save_books_to_mongodb(books: list[dict], mongo_collection: Collection = None):
	"""
	Saves a list of book dictionaries to MongoDB.
	Optionally accepts a pre-established MongoDB collection; otherwise,
	uses the globally managed MongoDB collection.

	Returns:
		A dictionary containing insertion summary (num_inserted, num_duplicates, num_errors).
	"""
	# Use the passed collection if provided, otherwise get the global one
	books_collection = mongo_collection if mongo_collection is not None else get_mongo_collection()

	if books_collection is None:  # If it's still None after trying to get it, log error and return
		module_logger.error("MongoDB collection not available. Cannot save books.")
		print_log("Error: MongoDB collection not available. Cannot save books.", "error")

	num_inserted = 0
	num_duplicates = 0
	num_errors = 0

	for book in books:
		try:
			result = books_collection.insert_one(book)
			if result.acknowledged:
				num_inserted += 1
				module_logger.info(f"Inserted book: {book.get('title', 'Unknown Title')} (ID: {result.inserted_id})")
			else:
				module_logger.warning(f"Insertion not acknowledged for {book.get('title', 'Unknown Title')}.")
				print_log(f"Warning: Insertion not acknowledged for {book.get('title', 'Unknown Title')}.", "warning")
				num_errors += 1
		except DuplicateKeyError:
			module_logger.info(f"Duplicate book found by hash '{book['hash']}'. Skipping insertion.")
			# print_log(f"Info: Duplicate book found by hash '{book['hash']}'. Skipping insertion.", "info")
			num_duplicates += 1
		except InvalidDocument as e:
			module_logger.error(f"Invalid document for insertion: {e}. Book: {book.get('title', 'Unknown Title')}",
			                    exc_info=True)
			print_log(f"Error: Invalid document for insertion: {e}. Book: {book.get('title', 'Unknown Title')}",
			          "error")
			num_errors += 1
		except OperationFailure as e:
			module_logger.error(f"MongoDB operation failed for {book.get('title', 'Unknown Title')}: {e}",
			                    exc_info=True)
			print_log(f"Error: MongoDB operation failed for {book.get('title', 'Unknown Title')}: {e}", "error")
			num_errors += 1
		except Exception as e:
			print(book)
			module_logger.error(f"Unexpected error during insertion of {book.get('title', 'Unknown Title')}: {e}",
			                    exc_info=True)
			print_log(f"Error: Unexpected error during insertion of {book.get('title', 'Unknown Title')}: {e}", "error")
			num_errors += 1

	module_logger.info(
		f"MongoDB insertion summary: {num_inserted} new, {num_duplicates} duplicate{'s' if num_duplicates != 1 else ''}, {num_errors} error{'s' if num_errors != 1 else ''}.")
	print_log(f"MongoDB insertion summary: {num_inserted} new, {num_duplicates} duplicates, {num_errors} errors.",
	          "success")


def check_amazon_asin_exists_in_db(asin: str, mongo_collection: Collection = None) -> bool:
	books_collection = mongo_collection if mongo_collection is not None else get_mongo_collection()

	if books_collection is None:
		module_logger.error("MongoDB collection not provided for duplicate check or not initialized.")
		print_log("Error: MongoDB collection not available for duplicate check.", "error")
		return False

	try:
		is_duplicate = books_collection.find_one({"asin": asin}) is not None
		if is_duplicate:
			module_logger.info(f"ASIN {asin} found in MongoDB Atlas database. Skipping detailed scrape.")
		return is_duplicate

	except Exception as e:
		module_logger.error(f"Error checking for duplicate Amazon book in DB by ASIN: {e}", exc_info=True)
		print_log(f"Error: Error checking for duplicate Amazon book in DB by ASIN: {e}", "error")
		return False


def check_book_exists_in_db(book_hash: str, mongo_collection: Collection = None) -> bool:
	"""
	Checks if a book with the given hash already exists in the database.
	"""
	books_collection = mongo_collection if mongo_collection is not None else get_mongo_collection()

	# module_logger.info(f"Debug: Type of books_collection in check_book_exists_in_db: {type(books_collection)}")
	# print_log(f"Debug: Type of MongoDB collection in duplicate check: {type(books_collection)}", "info")

	if books_collection is None:
		module_logger.error("MongoDB collection not provided for duplicate check or not initialized.")
		print_log("Error: MongoDB collection not available for duplicate check.", "error")
		return False

	try:
		return books_collection.find_one({"hash": book_hash}) is not None
	except Exception as e:
		module_logger.error(f"Error checking for duplicate book in DB: {e}", exc_info=True)
		print_log(f"Error: Error checking for duplicate book in DB: {e}", "error")
		return False


def update_book_isbn(books_collection: Collection, book_hash: str, new_isbn10: str = None, new_isbn13: str = None):
	"""
	Updates the ISBNs of an existing book in the database.
	This function expects an already connected collection to be passed to it.
	"""
	# This function is designed to receive an already valid collection.
	# If it's None, it implies an issue in the calling logic.
	if not books_collection:
		module_logger.error("MongoDB collection not available for ISBN update.")
		print_log("Error: MongoDB collection not available for ISBN update.", "error")
		return False

	update_fields = {}
	if new_isbn10 and new_isbn10 != "N/A":
		update_fields["isbn10"] = new_isbn10
	if new_isbn13 and new_isbn13 != "N/A":
		update_fields["isbn13"] = new_isbn13

	if not update_fields:
		module_logger.info(f"No valid ISBNs to update for hash: {book_hash}")
		print_log(f"Info: No valid ISBNs to update for hash: {book_hash}", "info")
		return False

	try:
		result = books_collection.update_one(
			{"hash": book_hash},
			{"$set": update_fields}
		)
		if result.modified_count > 0:
			module_logger.info(f"Updated ISBNs for book with hash '{book_hash}'.")
			print_log(f"Updated ISBNs for book with hash '{book_hash}'.", "info")
			return True
		else:
			module_logger.warning(f"Book with hash '{book_hash}' not found for ISBN update or no change needed.")
			print_log(f"Warning: Book with hash '{book_hash}' not found for ISBN update or no change needed.",
			          "warning")
			return False
	except Exception as e:
		module_logger.error(f"Error updating ISBNs for hash '{book_hash}': {e}", exc_info=True)
		print_log(f"Error: Error updating ISBNs for hash '{book_hash}': {e}", "error")
		return False


def ensure_unique_index_on_hash(books_collection: Collection):
	"""
	Ensures a unique index on the 'hash' field in the MongoDB collection.
	"""
	if books_collection is None:
		module_logger.error("MongoDB collection not available to ensure unique index.")
		return

	try:
		# Check if the index already exists before creating it
		if 'hash_unique_index' not in books_collection.index_information():
			books_collection.create_index("hash", unique=True, name='hash_unique_index')
			module_logger.info("Ensured unique index on 'hash' field.")
			print_log("Ensured unique index on 'hash' field.", "info")
		else:
			module_logger.info("Unique index on 'hash' field already exists.")
	except Exception as e:
		module_logger.error(f"Failed to ensure unique index on 'hash': {e}", exc_info=True)
		print_log(f"Error: Failed to ensure unique index on 'hash': {e}", "error")


async def check_for_new_books_before_scrape(books_from_search: list) -> list:
	"""
	Checks each book in the provided list against the MongoDB database
	to identify and return URLs of books that are new (not yet in the database).

	Args:
		books_from_search (list): A list of book dictionaries obtained from search,
								  each expected to have 'site', 'book_id', 'url', and 'hash'.

	Returns:
		list: A list of URLs for books that are considered new.
	"""
	# print_log("Executing pre-scrape deduplication.", "info")

	books_collection = get_mongo_collection()
	if books_collection is None:
		print_log("MongoDB collection is not available. Cannot check for new books.", "error")
		return []

	exists = True
	book_url = None
	new_book_urls = []

	# print_log(f"Checking for new books against MongoDB...", 'info')

	for book in books_from_search:
		site_name = book.get("site")
		book_title = book.get("title")

		if site_name == "amazon":
			asin = book.get("asin")
			book_url = book.get("url")
			exists = await asyncio.to_thread(check_amazon_asin_exists_in_db, asin, books_collection)

		if site_name == "leanpub":
			book_id = book.get("book_id")
			book_slug = book.get("slug")
			book_url = site_constants["leanpub"]["SINGLE_BOOK_API"].replace("[slug]", book_slug)
			exists = await asyncio.to_thread(check_leanpub_book_id_or_slug_exists_in_db, book_id, book_slug,
			                                 books_collection)

		if not exists:
			new_book_urls.append({"site": site_name, "book_url": book_url})
			print_log(f"{site_name.title()} - New book found: {book_title}", 'info')

		else:
			print_log(f"{site_name.title()} - Book already in database: {book_title}", 'warning')

	# print_log(f"Finished checking. Total new book URLs identified: {len(new_book_urls)}", "info")
	return new_book_urls
