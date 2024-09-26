import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient, server_api
from pymongo.errors import ServerSelectionTimeoutError, InvalidDocument, ConnectionFailure, InvalidName, \
    DuplicateKeyError


def save_to_atlas(books: list[dict]):
    load_dotenv()
    mongodb_uri = os.environ["MONGODB_URI_YAN"]
    tls_cert_file = os.environ["TLS_CERT_FILE_YAN"]
    try:
        client = MongoClient(mongodb_uri,
                             tls=True,
                             tlsCertificateKeyFile=tls_cert_file,
                             server_api=server_api.ServerApi('1'))
        db = client['bookscraper']
        collection = db['books']

        # Configure logging (choose a destination, e.g., console)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        logger = logging.getLogger(__name__)  # Get a logger instance

        logger.info("Using the 'books' collection in the 'bookscraper' database")
        print("Using the 'books' collection in the 'bookscraper' database")

        # Prepare an empty list to store successful insertions
        books_to_insert = []

        print("Checking for duplicates...")
        for book in books:
            try:
                # Attempt insert, raising an exception if duplicate hash exists
                result = collection.insert_one(book)
                books_to_insert.append(book)
                print("Added: ", book['title'])
            except DuplicateKeyError:
                print(f"Skipping duplicate book: {book['title']}, by {book['authors']}, {book['publication_year']}")

        if books_to_insert:
            print("Successfully inserted documents:")
            for doc in books_to_insert:
                print(doc["title"])  # Print titles of inserted documents
        else:
            print("No new documents inserted (all duplicates).")

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"Failed to connect to MongoDB Atlas: {e}")
    except (InvalidName, InvalidDocument) as e:
        logger.error(f"Error accessing database or collection: {e}")
    finally:
        client.close()
