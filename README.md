# BookScraper

Python-MongoDB book scraper to Scrap requested book information from Amazon, Leanpub and some other shops.

## Installation

```bash
pip install playwright==1.46.0 pymongo==4.8.0 Markdown==3.7 requests==2.32.3
```

or

```bash
pip install -r requirements.txt
```

## Usage

### 1. To scrape an existing .md file

````bash
python3 scrapemd.py
````

## How it works

### 1. Loading an .md file

- The scraper loads a specified markdown file.

For now, its URI is hardcoded, but we could change it to a CLI argument in a future iteration.
will parse an md file, line by line,

### 2. Parsing the .md file

The md file is read line-by-line and parsed for tokenization

#### Format expected:

- Book category line begins with '##'
- Book entry line begins with '*'
- Each book entry line has the following format:
    - \* [Book Title] (Book URL) (Author1, Auhtor2, ... , year)
- This will be parsed as a book document:

```bash
book = {
    "title": title,
    "hash": book_hash, # Unique, computed from title, authors, and year
    "isbn": None,
    "authors": [authors],
    "publication_year": year,
    "category": category,
    "url": url,
    "description": None,
    "tags": [None],
    "site": site, # Amazon.com, Leanrpub.com, etc.
    }
```

### Output:

Two outputs result from scrapemd.py:

1. A JSON file is created in the root directory, named "readmeBooks_YYYY-mm-dd_HH.MM.json".
2. A MongoDB Atlas collection is created (if non-existent) or updated
    - Connection parameters can be updated within the .env and save_to_mongo.py files

### Tests

Tests folder contains 5 tests for the mdparser.regex_parse function:

1. Test with Single Book with all details
2. Test with Multiple Books and Missing Year
3. Test with Invalid URL
4. Test with Multiple Authors

### Version notes:

**Current Version**: The remote file https://raw.githubusercontent.com/yuchdev/CppBooks/refs/heads/master/README.md is
hardcoded, but CLI arguments could be considered in the future.

