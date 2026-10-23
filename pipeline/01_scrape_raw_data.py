import os
import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

TARGET_CITIES = [
    "Amsterdam", "Athens", "Barcelona", "Berlin", "Budapest",
    "Lisbon", "London", "Paris", "Rome", "Vienna"
]

TARGET_PER_CITY = 50
CHECKPOINT_EVERY = 5
PAGE_LOAD_WAIT = 3
OUTPUT_FILE = "airbnb_dataset.xlsx"

# Weekend stay dates (late November 2026 - 2 nights)
CHECK_IN = "2026-11-27"
CHECK_OUT = "2026-11-29"

existing_ids = set()
all_data = []

# Safe load of previous checkpoint
if os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0:
    try:
        old_df = pd.read_excel(OUTPUT_FILE, engine="openpyxl")
        all_data = old_df.to_dict("records")
        existing_ids = set(str(item["Id"]) for item in all_data if "Id" in item and pd.notna(item["Id"]))
        print(f"Loaded {len(all_data)} existing records.")
    except Exception as exc:
        print(f"Error reading existing file: {exc}. Starting fresh.")
        all_data = []
        existing_ids = set()

# Stable Chrome Options
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--remote-debugging-pipe")
options.add_experimental_option("excludeSwitches", ["enable-automation"])

# Disable images for maximum performance
prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.default_content_setting_values.notifications": 2
}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

# Set base currency to USD
try:
    driver.get("https://www.airbnb.com")
    time.sleep(2)
    driver.add_cookie({"name": "currency", "value": "USD", "domain": ".airbnb.com"})
except Exception:
    pass

def extract_listing_details(driver, url):
    data = {}
    data["Id"] = url.split("/rooms/")[1].split("?")[0]
    
    page_text = driver.find_element(By.TAG_NAME, "body").text
    page_source = driver.page_source
    
    # 1. Price extraction (realSum) in USD
    data["realSum"] = None
    try:
        scripts = driver.find_elements(By.XPATH, "//script[@type='application/json']")
        for script in scripts:
            content = script.get_attribute("innerHTML")
            if "discountedPrice" in content or "priceString" in content or "rateDisplay" in content:
                found_prices = re.findall(r'"priceString":"([^"]+)"', content) or re.findall(r'"amount":(\d+)', content)
                if found_prices:
                    num = re.findall(r"\d+", str(found_prices[0]).replace(",", ""))
                    if num:
                        data["realSum"] = float(num[0])
                        break
    except Exception:
        pass

    if not data["realSum"]:
        price_patterns = [
            r"\$\s?([\d,]+)",
            r"([\d,]+)\s?\$",
            r"USD\s?([\d,]+)",
            r"([\d,]+)\s*(?:total|night|\/ night)"
        ]
        for pattern in price_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                raw_num = match.group(1).replace(",", "")
                data["realSum"] = float(raw_num)
                break

    # Validation: skip listing if price is absent
    if data["realSum"] is None:
        return None

    # 2. Room type & logical derived flags
    if "entire" in page_text.lower():
        data["room_type"] = "Entire home/apt"
    elif "shared room" in page_text.lower():
        data["room_type"] = "Shared room"
    else:
        data["room_type"] = "Private room"

    data["room_shared"] = (data["room_type"] == "Shared room")
    data["room_private"] = (data["room_type"] == "Private room")

    # 3. Person capacity
    guests_match = re.search(r"(\d+)\s+guest", page_text, re.IGNORECASE)
    data["person_capacity"] = int(guests_match.group(1)) if guests_match else 2

    # 4. Bedrooms
    bedrooms_match = re.search(r"(\d+)\s+bedroom", page_text, re.IGNORECASE)
    if bedrooms_match:
        data["bedrooms"] = int(bedrooms_match.group(1))
    elif "studio" in page_text.lower():
        data["bedrooms"] = 0
    else:
        data["bedrooms"] = 1

    # 5. Overall satisfaction rating
    rating_match = re.search(r"(\d\.\d{1,2})\s*★", page_text) or re.search(r"★\s*(\d\.\d{1,2})", page_text)
    if rating_match:
        data["guest_satisfaction_overall"] = float(rating_match.group(1))
    else:
        score_match = re.search(r"(\d\.\d{1,2})\s+out of 5", page_text)
        data["guest_satisfaction_overall"] = float(score_match.group(1)) if score_match else None

    # 6. Cleanliness rating
    cleanliness_match = re.search(r"Cleanliness\s*(\d(?:\.\d)?)", page_text, re.IGNORECASE)
    data["cleanliness_rating"] = float(cleanliness_match.group(1)) if cleanliness_match else 10.0

    # 7. Superhost status
    data["host_is_superhost"] = "Superhost" in page_text

    # 8. Geographic coordinates (lat / lng)
    data["lat"] = None
    data["lng"] = None
    
    lat_match = re.search(r'"lat":\s*(-?\d+\.\d+)', page_source) or re.search(r'"latitude":\s*(-?\d+\.\d+)', page_source)
    lng_match = re.search(r'"lng":\s*(-?\d+\.\d+)', page_source) or re.search(r'"longitude":\s*(-?\d+\.\d+)', page_source)
    
    if lat_match and lng_match:
        data["lat"] = float(lat_match.group(1))
        data["lng"] = float(lng_match.group(1))
    else:
        map_match = re.search(r'center=(-?\d+\.\d+)%2C(-?\d+\.\d+)', page_source)
        if map_match:
            data["lat"] = float(map_match.group(1))
            data["lng"] = float(map_match.group(2))

    return data

def save_dataset(data):
    if not data:
        return
    df = pd.DataFrame(data)
    df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")

try:
    for city in TARGET_CITIES:
        city_ids = set(str(item["Id"]) for item in all_data if item.get("city") == city and item.get("realSum") is not None)
        city_count = len(city_ids)
        
        if city_count >= TARGET_PER_CITY:
            print(f"Skipping {city}: already has {city_count} records.")
            continue

        print(f"\n--- Scraping city: {city} ({city_count}/{TARGET_PER_CITY}) ---")
        search_url = f"https://www.airbnb.com/s/{city}/homes?checkin={CHECK_IN}&checkout={CHECK_OUT}&currency=USD"
        driver.get(search_url)
        time.sleep(PAGE_LOAD_WAIT)

        page_number = 1

        while city_count < TARGET_PER_CITY:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            page_links = []
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href and "/rooms/" in href:
                        clean_url = href.split("?")[0]
                        listing_id = clean_url.split("/rooms/")[1]
                        if listing_id not in existing_ids and clean_url not in page_links:
                            page_links.append(clean_url)
                except Exception:
                    continue

            search_tab = driver.current_window_handle

            for base_url in page_links:
                if city_count >= TARGET_PER_CITY:
                    break

                listing_id = base_url.split("/rooms/")[1].split("?")[0]
                if listing_id in existing_ids:
                    continue

                target_url = f"{base_url}?check_in={CHECK_IN}&check_out={CHECK_OUT}&currency=USD"

                try:
                    driver.execute_script("window.open(arguments[0], '_blank');", target_url)
                    driver.switch_to.window(driver.window_handles[-1])
                    
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    time.sleep(1.5)
                    
                    details = extract_listing_details(driver, target_url)

                    if not details or details.get("realSum") is None:
                        print(f"[{city}] Skipped ID={listing_id}: Price unavailable.")
                        continue

                    details["city"] = city
                    all_data.append(details)
                    existing_ids.add(listing_id)
                    city_ids.add(listing_id)
                    city_count = len(city_ids)

                    print(f"[{city}] {city_count}/{TARGET_PER_CITY} | ID={listing_id} | Price=${details['realSum']} | Lat={details['lat']} | Lng={details['lng']}")

                    if len(all_data) % CHECKPOINT_EVERY == 0:
                        save_dataset(all_data)

                except Exception as exc:
                    print(f"Error processing {target_url}: {exc}")

                finally:
                    if len(driver.window_handles) > 1:
                        driver.close()
                    driver.switch_to.window(search_tab)

            if city_count >= TARGET_PER_CITY:
                break

            try:
                next_button = driver.find_element(
                    By.XPATH,
                    "//nav[@aria-label='Search results navigation']//a[contains(@aria-label, 'Next')] "
                    "| //nav[@aria-label='Search results navigation']//a[last()] "
                    "| //a[@aria-label='Next']"
                )
                driver.execute_script("arguments[0].click();", next_button)
                page_number += 1
                time.sleep(PAGE_LOAD_WAIT)
            except Exception:
                try:
                    target_page_btn = driver.find_element(By.XPATH, f"//nav//a[text()='{page_number + 1}']")
                    driver.execute_script("arguments[0].click();", target_page_btn)
                    page_number += 1
                    time.sleep(PAGE_LOAD_WAIT)
                except Exception:
                    break

        save_dataset(all_data)
        print(f"City {city} completed with {city_count} records.")

except KeyboardInterrupt:
    print("\nProcess interrupted manually. Saving collected data...")
finally:
    try:
        save_dataset(all_data)
        print(f"Successfully saved {len(all_data)} records to {OUTPUT_FILE}")
    except Exception as exc:
        print(f"Failed to save output file: {exc}")
    driver.quit()