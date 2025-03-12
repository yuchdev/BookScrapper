USER_AGENTS = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",

    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0",

    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15",

    # Edge (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.55",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36 Edg/93.0.961.47",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36 Edg/94.0.992.50",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.40",
]

site_constants = {
    "amazon": {
        "404_PAGE_TITLE": "not found",
        "BOOK_TITLE": "#productTitle",
        "AUTHORS": "#bylineInfo span.author.notFaded a",
        "AUTHORS_ALT": "._about-the-author-card_style_cardContentDiv__FXLPd ._about-the-author-card_carouselItemStyles_authorName__HSb1t h2",
        "ISBN10": "#rpi-attribute-book_details-isbn10 .rpi-attribute-value",
        "ISBN13": "#rpi-attribute-book_details-isbn13 .rpi-attribute-value",
        "TAGS": "#detailBulletsWrapper_feature_div ul li ul li a",
        "DETAILS_BUTTON": "a:has-text('Next slide of product details')",
        "PUBLICATION_DATE": "#rpi-attribute-book_details-publication_date div.rpi-attribute-value span",
        "DESCRIPTION": "#bookDescription_feature_div",
        "READ_MORE_LINK": "#bookDescription_feature_div .a-expander-prompt"
    },
    "leanpub": {
        "404_PAGE_TITLE": "not found",
        "BOOK_TITLE": "h3.book-hero__title",
        "AUTHORS": ".avatar-with-name__name",
        "AUTHORS_ALT": "",
        # "ISBN10": "",
        # "ISBN13": "",
        "TAGS": ".meta-list__item.categories li",
        "PUBLICATION_DATE": ".last-updated",
        "DESCRIPTION": ".about-book div.about-book__copy",
        "DESCRIPTION_ALT": ".book-hero__blurb",
        "READ_MORE_LINK": ""
    },
    "packtpub": {
        "404_PAGE_TITLE": "not found",
        "BOOK_TITLE": "h1.product-title",
        "AUTHORS": "div.authors span",
        "AUTHORS_ALT": "",
        # "ISBN10": "",
        "ISBN13": "div.product-page-rhs.desktop span.product-details-section-key:has-text('ISBN-13 :') + span.product-details-section-value",
        "TAGS": "div.product-page-rhs.desktop a",
        # "DETAILS_BUTTON": "",
        "PUBLICATION_DATE": "div.product-page-rhs.desktop span.product-details-section-key:has-text('Publication date :') + span.product-details-section-value",
        "DESCRIPTION": ".product-book-content-details h2:has-text('Description') + div.content-text",
        # "READ_MORE_LINK": ""
    },
    "oreilly": {
        "404_PAGE_TITLE": "",
        "BOOK_TITLE": "h1.t-title",
        "AUTHORS": "a.author-name",
        # "AUTHORS_ALT": "",
        "ISBN": "div.t-isbn",
        # "TAGS": "",
        # "DETAILS_BUTTON": "",
        "PUBLICATION_DATE": "ul.detail-product-information span.name:has-text('Release date:') + span.value",
        "DESCRIPTION": "#sbo-reader div.content span",
        # "READ_MORE_LINK": ""
    }
}
