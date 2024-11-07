import unittest
from tools.mdparser import regex_parse
from src.bookscraper.book_utils import hash_book


class TestMdParser(unittest.TestCase):

    def test_regex_parse_single_book_all_details(self):
        """
        Tests if the function can parse a markdown string with a single book entry containing title, url, author and year.
        """
        markdown_data = """
## C++ Primer Books
* [C++ Primer](https://www.example.com/cpp-primer) (Stroustrup, 2013)
      """
        expected_books = [
            {
                "title": "C++ Primer",
                "url": "https://www.example.com/cpp-primer",
                "authors": ["Stroustrup"],
                "publication_year": 2013,
                "category": "C++ Primer Books",
                "site": "www.example.com",
                "isbn": None,
                "description": None,
                "hash": hash_book("C++ Primer", ["Stroustrup"], 2013),
                "tags": [None],
            }
        ]
        books = regex_parse(markdown_data)
        self.assertEqual(books, expected_books)

    def test_regex_parse_multiple_books_missing_year(self):
        """
        Tests if the function can parse a markdown string with multiple book entries, where one book might be missing the year.
        """
        markdown_data = """
## Python Books
* [Learning Python](https://www.example.com/python-book) (Mark Lutz)
* [Fluent Python](https://www.example.com/fluent-python)
      """
        expected_books = [
            {
                "title": "Learning Python",
                "url": "https://www.example.com/python-book",
                "authors": ["Mark Lutz"],
                "publication_year": None,
                "category": "Python Books",
                "site": "www.example.com",
                "isbn": None,
                "description": None,
                "hash": hash_book("Learning Python", ["Mark Lutz"]),
                "tags": [None],
            },
            {
                "title": "Fluent Python",
                "url": "https://www.example.com/fluent-python",
                "authors": [None],
                "publication_year": None,
                "category": "Python Books",
                "site": "www.example.com",
                "isbn": None,
                "description": None,
                "hash": hash_book("Fluent Python"),
                "tags": [None],
            }
        ]
        books = regex_parse(markdown_data)
        self.assertEqual(books, expected_books)

    def test_regex_parse_missing_url(self):
        """
        Tests if the function handles a missing URL in the markdown data.
        """
        markdown_data = """
    ## Data Science Books
    * [Missing URL Book]( ) (Aurélien Géron, 2019)
        """
        expected_books = []
        books = regex_parse(markdown_data)
        self.assertEqual(books, expected_books)

    def test_regex_parse_multiple_authors(self):
        """
        Tests if the function can parse a markdown string with a book entry containing multiple authors.
        """
        markdown_data = """
## Machine Learning Books
* [Hands-On Machine Learning with Scikit-Learn, Keras & TensorFlow](https://www.example.com/ml-book) (Aurélien Géron, Bertrand Kiefer, Alexandre Barbu, 2021)
      """
        expected_books = [
            {
                "title": "Hands-On Machine Learning with Scikit-Learn, Keras & TensorFlow",
                "url": "https://www.example.com/ml-book",
                "authors": ['Aurélien Géron', "Bertrand Kiefer", "Alexandre Barbu"],
                "publication_year": 2021,
                "category": "Machine Learning Books",
                "site": "www.example.com",
                "isbn": None,
                "description": None,
                "hash": hash_book("Hands-On Machine Learning with Scikit-Learn, Keras & TensorFlow",
                                  ["Aurélien Géron", "Bertrand Kiefer", "Alexandre Barbu"], 2021),
                "tags": [None],
            }
        ]
        books = regex_parse(markdown_data)
        self.assertEqual(books, expected_books)

    def test_regex_parse_multiple_urls(self):
        """
        Tests if the function can parse a markdown string with a book entry containing multiple URLs.
        """
        markdown_data = """
## Programming Books
* [Programming in Python](https://www.example.com/python-book) (John Doe, https://www.example.com/python-book-2)
        """
        expected_books = [
            {
                "title": "Programming in Python",
                "url": "https://www.example.com/python-book",
                "authors": ["John Doe"],
                "publication_year": None,
                "category": "Programming Books",
                "site": "www.example.com",
                "isbn": None,
                "description": None,
                "hash": hash_book("Programming in Python", ["John Doe"]),
                "tags": [None],
            },
        ]
        books = regex_parse(markdown_data)
        self.assertEqual(books, expected_books)


if __name__ == "__main__":
    unittest.main()
