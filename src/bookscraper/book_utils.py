import hashlib
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient, server_api
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# Create a logger instance
logger = logging.getLogger('bookscraper')
logger.setLevel(logging.INFO)

# File Handler: Writes logs to a file
log_file_path = "bookscraper.log"
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)

# Stream Handler: Writes logs to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Message format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
if not logger.handlers:  # Prevent adding handlers multiple times if module is reloaded
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def print_log(text, status: str):
    """
    Logs the given text with color-coding based on the status, using the configured logger.
    This function is now a wrapper around the standard logging calls.
    """
    # ANSI escape codes for coloring console output
    RESET_COLOR_CODE = "\033[0m"
    COLORS = {
        "error": "\033[31m",  # Red
        "info": "\033[33m",  # Yellow
        "warning": "\033[35m",  # Magenta
        "debug": "\033[36m"  # Cyan
    }

    # Decide which logging method to call based on status
    if status == "error":
        logger.error(f"{COLORS.get(status, RESET_COLOR_CODE)}{text}{RESET_COLOR_CODE}")
    elif status == "info":
        logger.info(f"{COLORS.get(status, RESET_COLOR_CODE)}{text}{RESET_COLOR_CODE}")
    elif status == "warning":  # Added for potential future use
        logger.warning(f"{COLORS.get(status, RESET_COLOR_CODE)}{text}{RESET_COLOR_CODE}")
    elif status == "debug":  # Added for potential future use
        logger.debug(f"{COLORS.get(status, RESET_COLOR_CODE)}{text}{RESET_COLOR_CODE}")
    else:
        logger.info(f"{text}")  # Default to info if status is not recognized


def check_csv_write_permission(directory: str = '.') -> bool:
    """
    Checks if the application has write permissions in the specified directory.
    Attempts to create, write to, and delete a dummy file.
    Returns True if successful, False otherwise.
    """
    test_file_path = os.path.join(directory, "test_write_permission.tmp")
    try:
        with open(test_file_path, 'w') as f:
            f.write("test")
        os.remove(test_file_path)
        logger.info(f"Successfully verified write permission in '{directory}'.")
        return True
    except OSError as e:
        logger.error(f"Write permission test failed in '{directory}': {e}")
        print_log(
            f"Permission Error: Cannot write to the current directory ('{directory}'). Please ensure you have write access.",
            "error")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during CSV write permission test: {e}", exc_info=True)
        print_log("An unexpected error occurred during CSV write permission test. Check log for details.", "error")
        return False


def check_mongodb_connection() -> bool | None:
    """
    Attempts to establish and ping a MongoDB Atlas connection.
    Returns True if successful, False otherwise.
    """
    load_dotenv()  # Ensure .env variables are loaded
    mongodb_uri = os.environ.get("MONGODB_URI")
    tls_cert_file = os.environ.get("TLS_CERT_FILE")

    if not mongodb_uri:
        logger.error("MONGODB_URI not found in environment variables for MongoDB connection test.")
        print_log("MongoDB Check Error: MONGODB_URI not found in environment variables. Cannot test connection.",
                  "error")
        return False

    client = None
    try:
        if tls_cert_file and os.path.exists(tls_cert_file):
            client = MongoClient(mongodb_uri,
                                 tls=True,
                                 tlsCertificateKeyFile=tls_cert_file,
                                 server_api=server_api.ServerApi('1'),
                                 serverSelectionTimeoutMS=5000)  # Added timeout
        else:
            client = MongoClient(mongodb_uri,
                                 server_api=server_api.ServerApi('1'),
                                 serverSelectionTimeoutMS=5000)  # Added timeout

        client.admin.command('ping')
        logger.info("MongoDB connection test successful.")
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection test failed: {e}")
        print_log(
            f"MongoDB Connection Error: Failed to connect to MongoDB Atlas. Please check your MONGODB_URI, TLS certificate, and network. Details: {e}",
            "error")
        return False
    except Exception as e:
        logger.critical(f"An unexpected error occurred during MongoDB connection test: {e}", exc_info=True)
        print_log(
            "MongoDB Check Error: An unexpected error occurred during connection test. Check log for full traceback.",
            "error")
        return False
    finally:
        if client:
            client.close()


def extract_year_from_date(date_string: str) -> int | None:
    """
    Extracts the year from a date string.

    Args:
      date_string: The date string in any supported format (e.g., "2023-12-19", "December 17, 2019", "1995", "Apr 23, 2021", "September 2016").

    Returns:
      int: The extracted year, or None if the year cannot be extracted.
    """
    try:
        # Attempt to parse the date string using different formats
        for date_format in ["%Y-%m-%d", "%B %d, %Y", "%Y", "%b %d, %Y", "%B %Y"]:
            try:
                date_object = datetime.strptime(date_string, date_format)
                return date_object.year
            except ValueError:
                continue  # Try the next format
        logger.warning(f"Could not extract year from date string: '{date_string}' using known formats.")
        return None

    except Exception as e:
        logger.error(f"Error extracting year from '{date_string}': {e}")
        return None


def hash_book(title: str = "", authors: list = None, year=None) -> str:
    """
    Calculates a SHA-256 hash for a book based on its title, authors, and year.

    Args:
        title: The title of the book (required).
        authors: The authors of the book, separated by commas (required).
        year: The publication year of the book (optional, default is 0).

    Returns:
        A hexadecimal string representing the SHA-256 hash of the combined fields.
    """

    if authors is None:
        authors = []
    else:
        # Normalize and sort authors for consistent hashing
        authors = sorted([str(a).strip().lower() for a in authors if a is not None])

    try:
        if not title:
            logger.warning("Attempted to hash a book with no title. Hash will be based on empty title.")
            # raise ValueError("Title is required.") # Could raise an error, but warning might be better to hash incomplete entries

        year_str = str(year) if year is not None else ""

        # Join authors for consistent hashing
        authors_str = "|".join(authors)

        # Normalize hash input and proceed
        combined_fields = f"{title.strip().lower()}|{authors_str}|{year_str}"
        hash_object = hashlib.sha256()
        hash_object.update(combined_fields.encode('utf-8'))
        return hash_object.hexdigest()

    except Exception as e:
        logger.error(f"Error hashing book (title: '{title}', authors: {authors}, year: {year}): {e}")
        return ''
