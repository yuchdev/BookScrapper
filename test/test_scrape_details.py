# from playwright.sync_api import sync_playwright
from bookscraper.scrape_details import scrape_amazon


# def test_scrape_amazon(page):
#     page.goto("https://www.amazon.com/dp/0201717069")
#     title = page.locator(".product-title-heading").inner_text()
#     authors = [author.inner_text() for author in page.locator(".byLine a").all()]
#
#     print(title,authors)


def test_scrape_amazon_multiple_authors():
    # Arrange
    url = "https://www.amazon.com/dp/0134448235"  # Book with multiple authors
    expected_title = "C++ How to Program"
    expected_authors = ["Paul Deitel", "Harvey Deitel"]  # Only one author is expected in the test case

    # Act
    book_details = scrape_amazon(url)

    # Assert
    assert book_details is not None, "Scraping failed"
    assert book_details["title"] == expected_title, f"Expected title: {expected_title}, Actual: {book_details['title']}"
    assert book_details["authors"] == expected_authors, f"Expected authors: {expected_authors}, Actual: {book_details['authors']}"

