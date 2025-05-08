import logging
import urllib.parse
from playwright.sync_api import sync_playwright
from src.utils.helpers import get_config  # assumes this returns dict with `search_criteria`

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("indeed_scraper")


def connect_to_existing_browser():
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp("http://localhost:9222")
        if not browser.contexts:
            logger.error("No contexts found. Is Chrome running with --remote-debugging-port=9222?")
            playwright.stop()
            return None, None, None, None
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        return playwright, browser, context, page
    except Exception as e:
        logger.error(f"Failed to connect to existing browser: {e}")
        return None, None, None, None


def extract_job_listings(page):
    jobs = []
    try:
        selectors = [
            ".job_seen_beacon",
            "[data-testid='job-card']",
            "div[id^='job_']"
        ]
        for selector in selectors:
            cards = page.query_selector_all(selector)
            if not cards:
                continue
            for card in cards:
                try:
                    title_elem = card.query_selector("h2 a, [data-testid='jobTitle']")
                    if not title_elem:
                        continue
                    title = title_elem.inner_text().strip()
                    url = title_elem.get_attribute("href")
                    if url.startswith("/"):
                        url = f"https://ca.indeed.com{url}"
                    jobs.append({"title": title, "url": url})
                except Exception as e:
                    logger.warning(f"Card error: {e}")
            if jobs:
                break
        return jobs
    except Exception as e:
        logger.error(f"Error extracting jobs: {e}")
        return []


def search_jobs():
    config = get_config()
    criteria = config.get("search_criteria", {})
    job_titles = criteria.get("job_titles", [])
    locations = criteria.get("locations", [])
    date_posted = criteria.get("date_posted", "last_7_days")

    fromage_map = {
        "last_24_hours": "1",
        "last_3_days": "3",
        "last_7_days": "7",
        "last_14_days": "14",
        "any": ""
    }
    fromage = fromage_map.get(date_posted, "7")

    playwright, browser, context, page = connect_to_existing_browser()
    if not page:
        logger.error("Could not connect to browser. Abort.")
        return []

    all_jobs = []

    try:
        for title in job_titles:
            for location in locations:
                logger.info(f"Searching for '{title}' in '{location}'")
                query = urllib.parse.quote_plus(title)
                loc = urllib.parse.quote_plus(location)
                search_url = f"https://ca.indeed.com/jobs?q={query}&l={loc}&fromage={fromage}&radius=25"
                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

                # Optional wait for job cards to load
                try:
                    page.wait_for_selector(".job_seen_beacon", timeout=15000)
                except Exception:
                    logger.warning("Timeout waiting for job cards to load.")

                jobs = extract_job_listings(page)
                logger.info(f"Found {len(jobs)} job(s) for '{title}' in '{location}'")
                all_jobs.extend(jobs)

        return all_jobs

    finally:
        if playwright:
            try:
                playwright.stop()
            except:
                pass
