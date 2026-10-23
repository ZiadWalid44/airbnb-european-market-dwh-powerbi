import json
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

prefs = {"profile.managed_default_content_settings.images": 2}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=options
)

base_url = "https://www.airbnb.com/rooms/1562923345911232516"
sample_url = f"{base_url}?check_in=2026-11-06&check_out=2026-11-08"

driver.get(sample_url)
time.sleep(5)

data = {}
data["Id"] = base_url.split("/rooms/")[1].split("?")[0]

page_text = driver.find_element(By.TAG_NAME, "body").text
page_source = driver.page_source

data["realSum"] = None
try:
    scripts = driver.find_elements(By.XPATH, "//script[@type='application/json']")
    for script in scripts:
        content = script.get_attribute("innerHTML")
        if "discountedPrice" in content or "priceString" in content:
            found_prices = re.findall(
                r'"priceString":"([^"]+)"', content
            ) or re.findall(r'"amount":(\d+)', content)
            if found_prices:
                num = re.findall(r"\d+", str(found_prices[0]).replace(",", ""))
                if num:
                    data["realSum"] = float(num[0])
                    break
except Exception:
    pass

if not data["realSum"]:
    price_selectors = [
        "//span[contains(@class, '_1y74zjx')]",
        "//span[contains(text(), '$') or contains(text(), '€') or contains(text(), '£') or contains(text(), 'EGP')]",
        "//div[contains(@data-section-id, 'BOOK_IT_FLOATING')]//span",
    ]
    for xpath in price_selectors:
        try:
            elem = driver.find_element(By.XPATH, xpath)
            num = re.findall(r"\d+", elem.text.replace(",", ""))
            if num:
                data["realSum"] = float(num[0])
                break
        except Exception:
            continue

guests_match = re.search(r"(\d+)\s+guest", page_text, re.IGNORECASE)
data["person_capacity"] = int(guests_match.group(1)) if guests_match else 2

bedrooms_match = re.search(r"(\d+)\s+bedroom", page_text, re.IGNORECASE)
if bedrooms_match:
    data["bedrooms"] = int(bedrooms_match.group(1))
elif "studio" in page_text.lower():
    data["bedrooms"] = 0
else:
    data["bedrooms"] = 1

if "entire" in page_text.lower():
    data["room_type"] = "Entire home/apt"
elif "shared room" in page_text.lower():
    data["room_type"] = "Shared room"
else:
    data["room_type"] = "Private room"

data["room_shared"] = data["room_type"] == "Shared room"
data["room_private"] = data["room_type"] == "Private room"

rating_match = re.search(r"(\d\.\d{1,2})\s*★", page_text) or re.search(
    r"★\s*(\d\.\d{1,2})", page_text
)
if rating_match:
    data["guest_satisfaction_overall"] = float(rating_match.group(1))
else:
    score_match = re.search(r"(\d\.\d{1,2})\s+out of 5", page_text)
    data["guest_satisfaction_overall"] = (
        float(score_match.group(1)) if score_match else None
    )

cleanliness_match = re.search(
    r"Cleanliness\s*(\d(?:\.\d)?)", page_text, re.IGNORECASE
)
data["cleanliness_rating"] = (
    float(cleanliness_match.group(1)) if cleanliness_match else 10.0
)

data["host_is_superhost"] = "Superhost" in page_text

for key, value in data.items():
    print(f"{key}: {value}")

driver.quit()