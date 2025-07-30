import json
import time
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

CSS_CLASSES = {
    "overall_score": ".index__score__BktQY",
    "title": "h3.index__title__xakS9.h3-semibold",
    "date": "time[datetime]",
    "recommendation_block": ".index__recommendationBlock__2zhEJ",
    "employment_info": ".index__employmentInfoBlock__wuOtj",
    "factor": ".index__factor__Mo6xW",
    "factor_title": ".index__title__Rq0Po",
    "factor_text": ".index__plainText__JgbHE",
    "review_block": ".index__reviewBlock__I8pdb",
}

def extract_company_name_from_url(kn_url):

    match = re.search(r'/de/([^/]+)/', kn_url)
    if match:
        return match.group(1)
    return "unknown_company"

def generate_filename(company_name):
    scraping_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"scraped_reviews_{company_name}_{scraping_datetime}.json"


def is_review_within_last_2_years(review_year, review_month):

    if review_year is None:
        return True 

    current_date = datetime.now()
    cutoff_date = current_date - timedelta(days=2 * 365)


    review_date = datetime(review_year, review_month or 1, 1)
    return review_date >= cutoff_date

def parse_review_block(block, kn_url, review_order, company_name):
    review = {}

    review['review_id'] = f"{company_name}_{review_order}"
    review['kn_url'] = kn_url


    score_el = block.select_one(CSS_CLASSES["overall_score"])
    review['overall_score'] = float(score_el.text.replace(',', '.')) if score_el else None


    title_el = block.select_one(CSS_CLASSES["title"])
    review['title'] = title_el.text.strip() if title_el else None

    date_el = block.select_one(CSS_CLASSES["date"])
    if date_el:
        date_str = date_el.get('datetime', '')
        date_parts = date_str.split('T')[0].split('-')
        review['year'] = int(date_parts[0])
        review['month'] = int(date_parts[1])
    else:
        review['year'] = None
        review['month'] = None



    emp_info_el = block.select_one(CSS_CLASSES["employment_info"])
    if emp_info_el:
        emp_info_text = emp_info_el.text.strip()
        emp_type_el = emp_info_el.select_one('b')
        review['employee_type'] = emp_type_el.text.strip() if emp_type_el else None
        try:
            position_text = emp_info_el.text.replace(review['employee_type'], '', 1).strip()
            review['position'] = position_text if position_text else None
        except:
            review['position'] = None
    else:
        review['employee_type'] = None
        review['position'] = None

    review['subcategories'] = []
    factors = block.select(CSS_CLASSES["factor"])
    for f in factors:
        cat_title_el = f.select_one(CSS_CLASSES["factor_title"])
        if not cat_title_el:
            continue
        cat_title = cat_title_el.text.strip()
        text_el = f.select_one(CSS_CLASSES["factor_text"])
        cat_text = text_el.text.strip() if text_el else None
        
        if cat_text:
            review['subcategories'].append({cat_title: cat_text})

    return review


def get_all_reviews_for_url(kn_url, save_path=None, max_reviews=100):
    company_name = extract_company_name_from_url(kn_url)
    if save_path is None:
        save_path = '../data/' + generate_filename(company_name)
        
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(kn_url)
        reviews = []
        more_reviews_available = True
        review_counter = 1
    
        while more_reviews_available:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            review_blocks = soup.select(CSS_CLASSES["review_block"])

            for block in review_blocks:
                if len(reviews) >= max_reviews:
                    print(f"Maximum number of reviews ({max_reviews}) reached. Stopping scraping.")
                    more_reviews_available = False
                    break

                parsed = parse_review_block(block, kn_url, review_counter, company_name)
                if parsed.get('title'):
                    if is_review_within_last_2_years(parsed.get('year'), parsed.get('month')):
                        reviews.append(parsed)
                        review_counter += 1
                    else:
                        print("First review outside the last 2 years found. Stopping scraping.")
                        more_reviews_available = False
                        break

            print(f"Collected {len(reviews)} reviews so far...")            

            if not more_reviews_available:
                break

            try:
                load_more_link = soup.select_one("a.index__button__2PFpW")
                if load_more_link and load_more_link.get("href"):
                    next_page_url = load_more_link["href"]
                    full_next_page_url = f"https://www.kununu.com{next_page_url}"
                    print(f"Navigating to next page: {full_next_page_url}")
                    driver.get(full_next_page_url)
                    time.sleep(3)
                else:
                    print("No more 'Mehr Bewertungen lesen' button found. All reviews loaded.")
                    more_reviews_available = False
            except Exception as e:
                print(f"Error finding 'Mehr Bewertungen lesen' button: {e}")
                more_reviews_available = False

        print(f"Total reviews collected: {len(reviews)}")

        results = {kn_url: reviews}
        with open(save_path, "w") as f:
            json.dump(results, f, indent=2)
        return results
    finally:
        driver.quit()
