import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient, server_api
from pymongo.errors import ServerSelectionTimeoutError, InvalidDocument, ConnectionFailure, InvalidName, \
    DuplicateKeyError


def save_to_atlas(books: list[dict]):
    """Saves a list of book dictionaries to MongoDB Atlas, handling duplicates.

    Args:
        books (list[dict]): A list of dictionaries, where each dictionary represents a book.
            Each book dictionary should have at least the following keys:
                "title" (str): The title of the book.
                "hash" (str): A unique hash representing the book.
                "authors" (list): A list of authors of the book.
                "publication_year" (int): The publication year of the book.

    Returns:
        None. Prints messages to the console indicating the success or failure of the operation.
    """

    load_dotenv()
    mongodb_uri = os.environ["MONGODB_URI_YAN"]
    tls_cert_file = os.environ["TLS_CERT_FILE_YAN"]

    # Configure logging (choose a destination, e.g., console)
    logging.basicConfig(filename="bookscraper.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)  # Get a logger instance

    try:
        client = MongoClient(mongodb_uri,
                             tls=True,
                             tlsCertificateKeyFile=tls_cert_file,
                             server_api=server_api.ServerApi('1'))
        db = client['bookscraper']
        collection = db['books']

        logger.info("Using the 'books' collection in the 'bookscraper' database")
        print("Using the 'books' collection in the 'bookscraper' database")

        num_inserted = 0
        for book in books:
            try:
                # Attempt to insert the book using the hash as the unique key
                result = collection.insert_one(book)

                # Check if the insertion was successful (acknowledged and inserted_id exists)
                if result.acknowledged and result.inserted_id:
                    num_inserted += 1
                    print("Added:", book['title'])
                else:
                    print(f"Failed to insert book: {book['title']}. Unknown error.")
                    logger.error(f"Failed to insert book: {book['title']}. Unknown error.")

            except DuplicateKeyError:
                print(f"Skipping duplicate book: {book['title']}, by {book['authors']}, {book['publication_year']}")
            except (InvalidName, InvalidDocument) as e:
                logger.error(f"Error inserting document: {e}")
                print(f"Error inserting document: {e}")
                logger.error(f"Error inserting document: {e}")

        if num_inserted > 0:
            print(f"Successfully inserted {num_inserted} new documents.")
        else:
            print("No new documents inserted.")

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"Failed to connect to MongoDB Atlas: {e}")
        print(f"Failed to connect to MongoDB Atlas: {e}")
    finally:
        client.close()
