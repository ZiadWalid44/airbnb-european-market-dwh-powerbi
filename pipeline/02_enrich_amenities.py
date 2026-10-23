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

INPUT_FILE = "airbnb_dataset.xlsx"
OUTPUT_FILE = "airbnb_dataset_enriched.xlsx"

CHECK_IN = "2026-11-27"
CHECK_OUT = "2026-11-29"

# 1. قراءة الملف الحالي
if not os.path.exists(INPUT_FILE):
    print(f"الملف {INPUT_FILE} غير موجود!")
    exit()

df = pd.read_excel(INPUT_FILE, engine="openpyxl")
print(f"تم تحميل {len(df)} إعلاناً من {INPUT_FILE} بنجاح.")

# التحقق من وجود ملف مخرجات مسبق لاستئناف العمل لو انقطع السكربت
processed_ids = set()
if os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0:
    try:
        temp_df = pd.read_excel(OUTPUT_FILE, engine="openpyxl")
        if "number_of_reviews" in temp_df.columns:
            processed_ids = set(temp_df[temp_df["number_of_reviews"].notna()]["Id"].astype(str))
            df = temp_df
            print(f"تم استئناف العمل: {len(processed_ids)} إعلاناً تم تحديثها مسبقاً.")
    except Exception as e:
        print(f"تعذر استئناف ملف سابق، سنبدأ من جديد: {e}")

# 2. إعداد المتصفح
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_experimental_option("excludeSwitches", ["enable-automation"])

prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.default_content_setting_values.notifications": 2
}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

try:
    driver.get("https://www.airbnb.com")
    time.sleep(2)
    driver.add_cookie({"name": "currency", "value": "USD", "domain": ".airbnb.com"})
except Exception:
    pass

def extract_extra_features(driver):
    page_text = driver.find_element(By.TAG_NAME, "body").text
    lower_text = page_text.lower()
    
    extra = {}
    
    # 1. عدد المراجعات (Number of reviews)
    rev_match = re.search(r"(\d[\d,]*)\s+(?:reviews|review|مراجعة|تقييم)", page_text, re.IGNORECASE)
    extra["number_of_reviews"] = int(rev_match.group(1).replace(",", "")) if rev_match else 0

    # 2. نوع العقار (Property type)
    prop_match = re.search(r"(?:Entire|Private room in|Shared room in)\s+([A-Za-z\s]+)", page_text)
    if prop_match:
        extra["property_type"] = prop_match.group(1).strip().split("\n")[0]
    else:
        extra["property_type"] = "Apartment"

    # 3. أهم المرافق (Key Amenities)
    extra["has_wifi"] = "wifi" in lower_text
    extra["has_kitchen"] = "kitchen" in lower_text or "مطبخ" in lower_text
    extra["has_ac"] = "air conditioning" in lower_text or " ac " in lower_text or "تكييف" in lower_text

    # 4. رسوم النظافة (Cleaning fee) إن وجدت
    clean_fee_match = re.search(r"Cleaning fee[^\$\d]*\$?(\d[\d,]*)", page_text, re.IGNORECASE)
    extra["cleaning_fee"] = float(clean_fee_match.group(1).replace(",", "")) if clean_fee_match else 0.0

    return extra

# 3. المرور على الإعلانات وتحديثها
try:
    for idx, row in df.iterrows():
        listing_id = str(row["Id"])
        
        if listing_id in processed_ids:
            continue

        target_url = f"https://www.airbnb.com/rooms/{listing_id}?check_in={CHECK_IN}&check_out={CHECK_OUT}&currency=USD"
        
        try:
            driver.get(target_url)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(1.5)

            extra_data = extract_extra_features(driver)
            
            # تحديث قيم الصف الحالي
            for key, val in extra_data.items():
                df.at[idx, key] = val
                
            processed_ids.add(listing_id)
            print(f"[{len(processed_ids)}/{len(df)}] تم تحديث ID: {listing_id} | Reviews: {extra_data['number_of_reviews']} | Type: {extra_data['property_type']}")

            # حفظ تدريجي كل 10 إعلانات
            if len(processed_ids) % 10 == 0:
                df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")

        except Exception as e:
            print(f"خطأ أثناء تحديث الإعلان {listing_id}: {e}")

finally:
    df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
    print(f"\nتم الانتهاء وحفظ الملف المحدث بالكامل في: {OUTPUT_FILE}")
    driver.quit()