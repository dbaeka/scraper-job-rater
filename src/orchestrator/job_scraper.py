import logging
import random
import re
import time
import urllib.parse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from db.repository import JobRepository
from src.utils.helpers import get_config

repo = JobRepository()

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


def random_delay(level='s'):
    if level == 's':
        duration = random.randint(500, 1500)
    elif level == 'm':
        duration = random.randint(1500, 4000)
    elif level == 'l':
        duration = random.randint(4000, 8000)
    else:
        raise ValueError("Invalid delay level. Use 's', 'm', or 'l'.")

    time.sleep(duration / 1000.0)


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
        logger.info(f"Successfully connected to browser. Current page: {page.url}")
        return playwright, browser, context, page
    except Exception as e:
        logger.error(f"Failed to connect to existing browser: {e}")
        if 'playwright' in locals() and playwright:
            playwright.stop()
        return None, None, None, None


def extract_job_details_from_right_pane(page, job_id, title_from_card_left_pane):
    logger.info(f"Extracting details from right pane for job ID: {job_id} ('{title_from_card_left_pane}')")
    details = {"job_id": job_id, "title_from_card_left_pane": title_from_card_left_pane}

    right_pane_selector_prefix = 'div#jobsearch-ViewjobPaneWrapper '

    try:
        # Title from Right Pane
        title_elem = page.query_selector(
            f'{right_pane_selector_prefix}h2[data-testid="jobsearch-JobInfoHeader-title"] span, {right_pane_selector_prefix}h2.jobsearch-JobInfoHeader-title span')
        if not title_elem:  # Fallback to the h2 itself
            title_elem = page.query_selector(
                f'{right_pane_selector_prefix}h2[data-testid="jobsearch-JobInfoHeader-title"], {right_pane_selector_prefix}h2.jobsearch-JobInfoHeader-title')
        details["title_right_pane"] = title_elem.inner_text().strip(
            "-job post").strip() if title_elem else title_from_card_left_pane

        # Company Name
        company_elem = page.query_selector(f'{right_pane_selector_prefix}div[data-testid="inlineHeader-companyName"] a')
        if company_elem:
            details["company_name"] = company_elem.inner_text().strip()
        else:  # Fallback based on example structure
            company_info_container = page.query_selector(
                f'{right_pane_selector_prefix}div[data-testid="jobsearch-CompanyInfoContainer"]')
            if company_info_container:
                # Try to find the company name within the container, preferring an 'a' tag
                name_elem = company_info_container.query_selector(
                    'div > div:first-child > div:first-child a, div.css-1htivnk > div.css-178pnsu > div[data-company-name="true"] > span > a')
                if not name_elem:  # If no 'a' tag, try a more general span or div
                    name_elem = company_info_container.query_selector(
                        'div > div:first-child > div:first-child > span, div.css-1htivnk > div.css-178pnsu > div[data-company-name="true"]')
                details["company_name"] = name_elem.inner_text().strip() if name_elem else None
            else:
                details["company_name"] = None

        # Location
        location_text = None
        location_elem_rhp = page.query_selector(
            f'{right_pane_selector_prefix}div[data-testid="inlineHeader-companyLocation"] > div')
        if location_elem_rhp:
            location_text = location_elem_rhp.inner_text().strip()
        else:  # Fallback to #jobLocationSection if present
            location_section_elem = page.query_selector(
                f'{right_pane_selector_prefix}div#jobLocationText div[data-testid="jobsearch-JobInfoHeader-companyLocation"]')
            if location_section_elem:
                location_text = location_section_elem.inner_text().strip()
        details["location"] = location_text

        # Pay
        pay_text = None
        salary_info_type_combo_elem = page.query_selector(f'{right_pane_selector_prefix}div#salaryInfoAndJobType')
        if salary_info_type_combo_elem:
            pay_span_elem = salary_info_type_combo_elem.query_selector('span')
            if pay_span_elem:
                pay_text = pay_span_elem.inner_text().strip()

        if not pay_text:  # Try #jobDetailsSection
            job_details_section = page.query_selector(f'{right_pane_selector_prefix}div#jobDetailsSection')
            if job_details_section:
                pay_detail_elem = job_details_section.query_selector(
                    'div[aria-label="Pay"] span, div[aria-label="Pay"] li span')
                if pay_detail_elem:
                    pay_text = pay_detail_elem.inner_text().strip()
        details["pay"] = pay_text

        # Job Type
        job_type_text = None
        if salary_info_type_combo_elem:
            job_type_span_elem = salary_info_type_combo_elem.query_selector('span')
            if job_type_span_elem:
                job_type_text = job_type_span_elem.inner_text().strip().replace("-", "").strip()
            elif details["pay"]:  # If pay was in combo, try to deduce job type
                full_combo_text = salary_info_type_combo_elem.inner_text().strip()
                if full_combo_text.startswith(details["pay"]):
                    potential_job_type = full_combo_text[len(details["pay"]):].strip()
                    if potential_job_type.startswith("-"):
                        job_type_text = potential_job_type[1:].strip()

        if not job_type_text:  # Try #jobDetailsSection
            job_details_section = page.query_selector(f'{right_pane_selector_prefix}div#jobDetailsSection')
            if job_details_section:
                job_type_detail_elem = job_details_section.query_selector(
                    'div[aria-label="Job type"] span, div[aria-label="Job type"] li span')
                if job_type_detail_elem:
                    job_type_text = job_type_detail_elem.inner_text().strip()
        details["job_type"] = job_type_text

        # Shift and Schedule
        shift_schedule_items = []
        job_details_section_for_schedule = page.query_selector(f'{right_pane_selector_prefix}div#jobDetailsSection')
        if job_details_section_for_schedule:
            schedule_section_aria = job_details_section_for_schedule.query_selector(
                'div[aria-label="Shift and schedule"]')
            if schedule_section_aria:
                items = schedule_section_aria.query_selector_all(
                    'ul li span, ul li div[data-testid*="-tile"] span, ul li span')
                for item in items:
                    text = item.inner_text().strip()
                    if text: shift_schedule_items.append(text)
        details["shift_and_schedule"] = ", ".join(
            list(dict.fromkeys(shift_schedule_items))) if shift_schedule_items else None

        # Benefits
        benefits_items = []
        benefits_section_container = page.query_selector(
            f'{right_pane_selector_prefix}div#benefits[data-testid="benefits-test"]')
        if benefits_section_container:
            items = benefits_section_container.query_selector_all('ul li')
            for item in items:
                text = item.inner_text().strip()
                if text: benefits_items.append(text)
        details["benefits"] = ", ".join(list(dict.fromkeys(benefits_items))) if benefits_items else None

        # Full Job Description
        desc_elem = page.query_selector(f'{right_pane_selector_prefix}div#jobDescriptionText')
        details["full_job_description_html"] = desc_elem.inner_html().strip() if desc_elem else None
        details["full_job_description_text"] = desc_elem.inner_text().strip() if desc_elem else None

        logger.info(
            f"Successfully extracted: Title='{details.get('title_right_pane')}', Company='{details.get('company_name')}', Location='{details.get('location')}'")
        return details

    except Exception as e:
        logger.error(
            f"Error extracting details from right pane for job ID {job_id} ('{title_from_card_left_pane}'): {e}",
            exc_info=True)
        # Return whatever was collected along with an error message
        details["extraction_error"] = str(e)
        return details


def search_jobs():
    config = get_config()
    criteria = config.get("search_criteria", {})
    job_titles_search = criteria.get("job_titles", [])
    locations_search = criteria.get("locations", [])
    salary_min = criteria.get("salary_min", None)
    job_types = criteria.get("job_types", [])

    fromsalary_map = {
        "60000": "$60,000+",
        "80000": "$80,000+",
        "100000": "$100,000+",
    }
    fromsalary = fromsalary_map.get(salary_min, None)

    job_types_map = {
        "full_time": "filter-jobtype1-0",
        "part_time": "filter-jobtype1-5",
        "contract": "filter-jobtype1-2",
        "temporary": "filter-jobtype1-4",
        "internship": "filter-jobtype1-6",
        "permanent": "filter-jobtype1-1",
    }
    job_types = [job_types_map.get(job_type, None) for job_type in job_types]

    playwright, browser, context, page = connect_to_existing_browser()
    if not page:
        logger.error("Could not connect to browser. Aborting.")
        return []

    all_extracted_jobs_details = []
    processed_job_ids_global = set()

    for search_title in job_titles_search:
        for locations in locations_search:
            fromage_map = {
                "last_24_hours": "Last 24 hours",
                "last_3_days": "Last 3 days",
                "last_7_days": "Last 7 days",
                "last_14_days": "Last 14 days",
                "any": ""
            }
            search_location = locations.get("location", "Ontario")
            date_posted = locations.get("date_posted", "any")

            fromage = fromage_map.get(date_posted, "Last 7 days")

            logger.info(f"Initiating search for '{search_title}' in '{search_location}' (last {fromage} days)")
            try:
                page.wait_for_selector("form#jobsearch", timeout=15000)

                job_input = page.query_selector("input[name='q']")
                job_input.fill(search_title)

                location_input = page.query_selector("input[name='l']")
                location_input.fill(search_location)

                find_button = page.query_selector("form#jobsearch button[type='submit']")
                find_button.click()

                page.wait_for_selector("div#mosaic-provider-jobcards ul", timeout=20000)
                logger.info("Search form submitted and results loaded")

                if date_posted != "any" and date_posted != "":
                    try:
                        logger.info(f"Applying {fromage} filter for date posted")

                        date_filter_button = page.wait_for_selector("button#fromAge_filter_button", timeout=20000)
                        date_filter_button.click()
                        random_delay('s')
                        page.wait_for_selector(
                            "div[role='menu'][aria-labelledby='fromAge_filter_button']:not([hidden])",
                            timeout=10000
                        )

                        age_option = page.wait_for_selector(f"a[aria-label='{fromage}']", timeout=20000)
                        age_option.click()

                        # Wait for results to reload
                        page.wait_for_selector("div#mosaic-provider-jobcards ul", timeout=20000)
                        logger.info(f"'{fromage}' filter applied and results reloaded")
                        random_delay('s')
                    except PlaywrightTimeoutError:
                        logger.warning("Timeout while trying to apply 'Last 24 hours' filter")
                    except Exception as e:
                        logger.warning(f"Failed to apply 'Last 24 hours' filter: {e}")

                if salary_min and salary_min != "":
                    try:
                        logger.info(f"Applying {fromsalary} filter for pay")

                        pay_filter_button = page.wait_for_selector("button#salaryType_filter_button", timeout=20000)
                        pay_filter_button.click()
                        random_delay('s')
                        page.wait_for_selector(
                            "div[role='menu'][aria-labelledby='salaryType_filter_button']:not([hidden])",
                            timeout=10000
                        )

                        pay_option = page.wait_for_selector(f"a[aria-label='{fromsalary}']", timeout=20000)
                        pay_option.click()

                        # Wait for results to reload
                        page.wait_for_selector("div#mosaic-provider-jobcards ul", timeout=20000)
                        logger.info(f"'{fromsalary}' filter applied and results reloaded")
                        random_delay('s')
                    except PlaywrightTimeoutError:
                        logger.warning("Timeout while trying to apply 'Last 24 hours' filter")
                    except Exception as e:
                        logger.warning(f"Failed to apply 'Last 24 hours' filter: {e}")
                if job_types:
                    try:
                        logger.info(f"Applying job type filter: {', '.join(job_types)}")

                        # Open the Job Type filter dialog
                        job_type_filter_button = page.wait_for_selector("button#filter-jobtype1", timeout=20000)
                        job_type_filter_button.click()
                        random_delay('s')
                        page.wait_for_selector(
                            "div[role='dialog'][aria-label='Edit Job type filter selection']:not([hidden])",
                            timeout=10000
                        )

                        # Check each checkbox by ID
                        for job_type_id in job_types:
                            checkbox = page.query_selector(f"input#{job_type_id}")
                            if checkbox:
                                is_checked = checkbox.is_checked()
                                if not is_checked:
                                    checkbox.click()
                                    page.wait_for_timeout(200)
                                logger.info(f"Selected job type checkbox: {job_type_id}")
                            else:
                                logger.warning(f"Checkbox with ID '{job_type_id}' not found")

                        # Click the "Update" button to apply the filter
                        update_button = page.query_selector("button[type='submit'][form='filter-jobtype1-menu']")
                        if update_button:
                            update_button.click()
                            logger.info("Clicked Update to apply job type filter")
                            page.wait_for_selector("div#mosaic-provider-jobcards ul", timeout=20000)
                        else:
                            logger.warning("Update button not found in job type filter dialog")
                        random_delay('s')
                    except PlaywrightTimeoutError:
                        logger.warning("Timeout while trying to apply job type filter")
                    except Exception as e:
                        logger.warning(f"Failed to apply job type filter: {e}")
            except PlaywrightTimeoutError:
                logger.error("Timeout waiting for search form or job results to load.")
                continue
            except Exception as e:
                logger.error(f"Error navigating to page: {e}")
                continue

            logger.info(f"Page loaded. Starting extraction for '{search_title}' in '{search_location}'.")

            while True:
                # Selector for individual job card containers (list items)
                all_li_elements = page.query_selector_all("div#mosaic-provider-jobcards ul > li")

                job_card_list_items = [
                    li for li in all_li_elements
                    if li.query_selector("div.cardOutline") is not None
                ]

                if not job_card_list_items:
                    job_card_list_items = page.query_selector_all("div.job_seen_beacon")
                    logger.warning(
                        f"Primary <li> selector found no cards. Found {len(job_card_list_items)} with fallback 'div.job_seen_beacon'.")

                if not job_card_list_items:
                    logger.warning(f"No job cards found on the page for '{search_title}' in '{search_location}'.")
                    break

                logger.info(f"Found {len(job_card_list_items)} potential job card LIs/elements.")

                for i, card_li_element in enumerate(job_card_list_items):
                    job_jk = None
                    title_from_card = "Unknown Title (Card)"
                    clickable_element = None
                    job_url = None

                    anchor_tag = card_li_element.query_selector("h2.jobTitle a[data-jk], a.jcs-JobTitle[data-jk]")
                    card_outline_div = card_li_element.query_selector("div.cardOutline")

                    if anchor_tag:
                        job_jk = anchor_tag.get_attribute("data-jk")
                        title_span = anchor_tag.query_selector("span[title]")
                        if title_span:
                            title_from_card = title_span.get_attribute("title")
                        else:
                            title_from_card = anchor_tag.inner_text()
                        clickable_element = anchor_tag
                        href = anchor_tag.get_attribute("href")
                        if href:
                            job_url = urllib.parse.urljoin("https://ca.indeed.com", href)
                    elif card_outline_div:  # If no direct anchor, check the cardOutline div
                        job_jk_on_card = card_outline_div.get_attribute("data-jk")
                        if job_jk_on_card:  # data-jk might be on the div itself
                            job_jk = job_jk_on_card
                        else:  # Or try to extract from class="... job_THE_JK ..."
                            card_classes = card_outline_div.get_attribute("class")
                            if card_classes:
                                match = re.search(r'\bjob_([a-f0-9]{16})\b', card_classes)
                                if match: job_jk = match.group(1)

                        if job_jk:  # If we got a JK from the card div
                            # Try to find title within this card
                            title_elem_on_card = card_outline_div.query_selector(
                                "h2.jobTitle span[title], h2.jobTitle a span[title]")
                            if title_elem_on_card:
                                title_from_card = title_elem_on_card.get_attribute("title")
                            else:  # Fallback for title
                                title_elem_text = card_outline_div.query_selector("h2.jobTitle span, h2.jobTitle a")
                                if title_elem_text: title_from_card = title_elem_text.inner_text()
                            clickable_element = card_outline_div

                    if not job_jk:
                        logger.warning(f"Card {i + 1}: Could not determine job ID (data-jk). Skipping.")
                        continue

                    if job_jk in processed_job_ids_global or repo.job_exists(job_jk):
                        logger.info(
                            f"Card {i + 1}: Job ID {job_jk} ('{title_from_card.strip()}') already processed. Skipping.")
                        continue

                    if not clickable_element:  # If jk was found but no specific clickable element, try the card_li_element itself
                        clickable_element = card_li_element
                        logger.warning(
                            f"Card {i + 1}: Using LI element as clickable target for '{title_from_card.strip()}'.")

                    title_from_card = title_from_card.strip()
                    logger.info(
                        f"Processing card {i + 1}/{len(job_card_list_items)}: '{title_from_card}' (ID: {job_jk})")

                    try:
                        clickable_element.scroll_into_view_if_needed(timeout=5000)
                        page.wait_for_timeout(200)  # Brief pause before click
                        clickable_element.click(timeout=10000,
                                                force=True)  # Force might be needed if overlays exist
                        logger.info(f"Clicked on job card: '{title_from_card}'")
                    except Exception as click_err:
                        logger.error(f"Failed to click on job card '{title_from_card}' (ID: {job_jk}): {click_err}")
                        continue

                    try:
                        # Wait for the title in the right pane to be visible
                        right_pane_title_selector = 'div#jobsearch-ViewjobPaneWrapper h2.jobsearch-JobInfoHeader-title'
                        page.wait_for_selector(right_pane_title_selector, timeout=5000, state="visible")

                        logger.info(f"Right pane appears updated for: '{title_from_card}'")
                        page.wait_for_timeout(1200)  # Allow JS to fully render content after visibility
                    except PlaywrightTimeoutError:
                        logger.warning(
                            f"Timeout waiting for right pane content to fully load for '{title_from_card}' (ID: {job_jk}). Attempting extraction with potentially incomplete data.")
                    except Exception as e:
                        logger.warning(
                            f"Error during wait for right pane for '{title_from_card}' (ID: {job_jk}): {e}. Attempting extraction.")

                    job_details_data = extract_job_details_from_right_pane(page, job_jk, title_from_card)
                    if job_details_data:
                        job_details_data["job_url"] = job_url
                        processed_job_ids_global.add(job_jk)
                        try:
                            repo.insert_job(job_details_data)
                            logger.info(f"Inserted job '{job_details_data.get('title_right_pane')}' into database.")
                        except Exception as db_err:
                            logger.error(f"Failed to insert job into database: {db_err}")
                    random_delay('m')

                # Check if there's a "Next" button to load more jobs
                try:
                    next_button = page.query_selector("a[data-testid='pagination-page-next']")
                    if next_button and next_button.is_visible():
                        logger.info("Next button found. Clicking to go to next page...")
                        next_button.scroll_into_view_if_needed(timeout=5000)
                        page.wait_for_timeout(500)
                        next_button.click()
                        page.wait_for_selector("div#mosaic-provider-jobcards ul", timeout=20000)
                        random_delay('m')
                    else:
                        logger.info("No next page button found. Pagination complete.")
                        break
                except Exception as e:
                    logger.warning(f"Error clicking next page: {e}")
                    break

    return all_extracted_jobs_details
