from playwright.sync_api import sync_playwright


def configure(config):
    config.test_dir = "tests"
    config.timeout = 30000
    config.use.headless = False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Run in headed mode for debugging
        # ... your test logic here ...
        browser.close()


if __name__ == "__main__":
    main()
