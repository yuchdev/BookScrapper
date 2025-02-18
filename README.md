# BookScraper

Python-MongoDB book scraper to Scrap requested book information from Amazon, Leanpub and some other shops.

## Installation

```
pip install -r .\requirements.txt
```

## Usage

in the project's root directory, scrape_existing_books.py allows to scrape a list of books from a CSV file:

Example usage:

```
python .\scrape_existing_books.py -f ".\input_links.csv"
```

Note: The scraper expects a column called 'url' in the CSV file.

### Book Sites Supported

At this stage, the scraper supports:

1. amazon.com
2. packtpub.com
3. leanpub.com
4. oreilly.com

### Output

At this stage, the scraper will output a file called "books.csv" in the directory from where scrape_existing_books.py is
executed. The file contains the results of the scrape, with the following fields, where applicable:

authors, description, hash, isbn10, isbn13, publication_date, site, summary, tags, title, and url.

At a subsequent iteration, the option to store the results within MongoDB will be added.

### Tests

Tests are contained within the ```test``` folder and shall be subsequently added for each site scraped.
