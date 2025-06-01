import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient, server_api
from pymongo.errors import ServerSelectionTimeoutError, InvalidDocument, ConnectionFailure, DuplicateKeyError, \
    OperationFailure, InvalidName

# Import print_log from book_utils for colored console output
from src.bookscraper.book_utils import print_log

# Configure logging for the database module
# This logger will write to the consolidated log file as configured in book_utils
logger = logging.getLogger(__name__)


def save_books_to_mongodb(books: list[dict]) -> None:
    """
    Saves a list of book dictionaries to a MongoDB Atlas cluster.
    Assumes MONGODB_URI and TLS_CERT_FILE are set in environment variables or .env file.
    """
    load_dotenv()
    mongodb_uri = os.environ.get("MONGODB_URI")
    tls_cert_file = os.environ.get("TLS_CERT_FILE")

    if not mongodb_uri:
        logger.critical("MONGODB_URI not found in environment variables. Cannot connect to MongoDB.")
        print_log("Error: MONGODB_URI not found in environment variables. Aborting MongoDB save.", "error")
        return

    client = None
    try:
        if tls_cert_file and os.path.exists(tls_cert_file):
            logger.info("Attempting to connect to MongoDB Atlas using TLS certificate.")
            print_log("Connecting to MongoDB Atlas (secure connection)...", "info")
            client = MongoClient(mongodb_uri,
                                 tls=True,
                                 tlsCertificateKeyFile=tls_cert_file,
                                 server_api=server_api.ServerApi('1'))
        else:
            logger.warning(
                "TLS_CERT_FILE not provided or file not found. Connecting to MongoDB without TLS certificate key file. This might not be secure in production.")
            print_log("Warning: TLS_CERT_FILE not found or invalid. Connecting to MongoDB without TLS certificate.",
                      "warning")
            client = MongoClient(mongodb_uri, server_api=server_api.ServerApi('1'))

        # The ping command is used to confirm that the connection has been established.
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB!")
        print_log("Successfully connected to MongoDB!", "info")

        db = client['bookscraper']
        collection = db['books']

        logger.info("Using the 'books' collection in the 'bookscraper' database.")
        print_log("Using the 'books' collection in the 'bookscraper' database...", "info")

        num_inserted = 0
        num_duplicates = 0
        num_errors = 0

        # Create unique index if it doesn't exist
        try:
            collection.create_index("hash", unique=True)
            logger.info("Ensured unique index on 'hash' field.")
            print_log("Ensured unique index on 'hash' field for efficient duplicate checking.", "info")
        except Exception as e:
            logger.error(f"Error creating unique index on 'hash': {e}")
            print_log(f"Error creating unique index on 'hash': {e}", "error")

        for book in books:
            if not book or not book.get("hash"):
                logger.warning(f"Skipping book due to missing data or hash: {book}")
                print_log(f"Skipping a book with missing data or hash. (Check log for details)", "warning")
                continue

            try:
                result = collection.insert_one(book)

                if result.acknowledged and result.inserted_id:
                    num_inserted += 1
                    logger.info(f"Inserted new book: {book.get('title', 'Unknown Title')}")
                    print_log(f"Added: {book.get('title', 'Unknown Title')}", "info")
                else:
                    logger.error(f"Failed to insert book: {book.get('title', 'Unknown Title')}. Unknown error.")
                    print_log(f"Failed to insert book: {book.get('title', 'Unknown Title')}. Unknown error.", "error")

            except DuplicateKeyError:
                num_duplicates += 1
                logger.info(f"Skipping duplicate book: {book.get('title', 'Unknown Title')}")
                print_log(
                    f"Skipping duplicate: {book.get('title', 'Unknown Title')} by {book.get('authors', 'Unknown Authors')} ({book.get('year', 'Unknown Year')})",
                    "warning")
            except (InvalidName, InvalidDocument, OperationFailure) as e:
                num_errors += 1
                logger.error(
                    f"Error inserting document (invalid data/operation): {book.get('title', 'Unknown Title')} - {e}")
                print_log(f"Error inserting document (invalid data): {book.get('title', 'Unknown Title')} - {e}",
                          "error")
            except Exception as e:  # Catch any other unexpected errors during single insert
                num_errors += 1
                logger.exception(
                    f"An unexpected error occurred during insertion of book {book.get('title', 'Unknown Title')}.")
                print_log(
                    f"Unexpected error during insertion of {book.get('title', 'Unknown Title')}. Check log for details.",
                    "error")

        logger.info(f"MongoDB insertion summary: {num_inserted} new, {num_duplicates} duplicates, {num_errors} errors.")
        print_log(f"MongoDB Insertion Summary:", "info")
        print_log(f"  {num_inserted} new documents successfully inserted.", "info")
        print_log(f"  {num_duplicates} duplicate documents skipped.", "info")
        if num_errors > 0:
            print_log(f"  Encountered {num_errors} errors during insertion. Check log for details.", "error")


    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.critical(f"Failed to connect to MongoDB Atlas: {e}")
        print_log(
            f"Critical Error: Failed to connect to MongoDB Atlas. Please check your connection string and network. Details: {e}",
            "error")
    except Exception as e:
        logger.critical(f"An unexpected error occurred during MongoDB operation: {e}", exc_info=True)
        print_log(
            f"Critical Error: An unexpected error occurred during MongoDB operation. Please check the log file for full traceback. Details: {e}",
            "error")
    finally:
        if client:
            client.close()
            logger.info("MongoDB connection closed.")
            print_log("MongoDB connection closed.", "info")
