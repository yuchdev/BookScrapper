# BookScraper

Python-MongoDB book scraper to Scrap requested book information from Amazon, Leanpub and some other shops.

## Installation

### 1. Create and activate a virtual environment:

#### Windows

cd path\to\your\project

`python -m venv venv`

`venv\Scripts\activate`

#### Linux/MacOS

cd path/to/your/project

`python3 -m venv venv`

`source venv/bin/activate`

### 2. Install required dependencies

`pip install -r .\requirements.txt`

## Usage

At this stage, in the project's root directory, scrape_existing_books.py allows to scrape a list of books from a CSV
file which contains a list of URLS.

Expected format of the CSV file:

```
url
https://en.cppreference.com/w/
https://github.com/isocpp/CppCoreGuidelines/blob/master/CppCoreGuidelines.md
https://isocpp.org/faq
https://www.amazon.com/dp/0321714113
https://www.amazon.com/dp/0138308683
https://www.amazon.com/dp/B00LZW07P0
...

```

scrape_existing_books.py will scrape the URLs for the book details each. For the moment, it does so by batches of 10, as
printed to the stdout display. Performance considerations in subsequent iterations may see either/or this batch number
customizable or the usage of a queue implemented.

Output:

1. books.csv, in the same directory, with the scraped book details
2. failed_books.csv, in the same directory, with the URLs that failed to be scraped as books

This failed_books.csv allows the user to manually investigate the issues. At a later iteration, there may be a way to
scrape this file (or another one) to add to books.csv, thereby covering false-negative and amended source URL scenarios.

Syntax:
`python scrape_existing_books.py -f <urls.csv>`

Where: -f, --file is the CSV file containing the Book URLs (required).

### Example usage:

`python .\scrape_existing_books.py -f ".\input_links.csv"`

### Book Sites Supported

At this stage, the scraper supports:

1. amazon.com
2. packtpub.com
3. leanpub.com
4. oreilly.com

## Output Specifications

At this stage, the scraper will output a file called "books.csv" in the directory from where scrape_existing_books.py is
executed. The file contains the results of the scrape, with the following fields, where applicable:

authors, description, hash, isbn10, isbn13, publication_date, site, summary, tags, title, and url.

At a subsequent iteration, the option to store the results within MongoDB will be added.

## Tests

Tests are contained within the ```test``` folder and are a not fully integrated at this stage.

## Note on Performance

At this stage, tests have shown an average of ~3.7s per Amazon book URL. This includes waiting periods to avoid being
flagged by anti-bot measures. Although not 100% stable, most trial runs show a 99-100% accuracy.
