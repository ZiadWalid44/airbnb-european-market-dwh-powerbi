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

url = "https://www.airbnb.com/s/Amsterdam--Netherlands/homes"
driver.get(url)
time.sleep(4)

listing_urls = set()
page = 1

while len(listing_urls) < 50:
    # تمرير لأسفل الصفحة لضمان تحميل جميع الكروت وشريط الترقيم
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # استخراج روابط الإعلانات
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        try:
            href = link.get_attribute("href")
            if href and "/rooms/" in href:
                clean_url = href.split("?")[0]
                listing_urls.add(clean_url)
        except Exception:
            continue

    print(f"الصفحة {page}: إجمالي الروابط الحالية = {len(listing_urls)}")

    if len(listing_urls) >= 50:
        break

    # الضغط على زر الصفحة التالية
    try:
        # البحث عن زر السهم التالي أو رابط الصفحة القادمة
        next_button = driver.find_element(
            By.XPATH,
            "//nav[@aria-label='Search results navigation']//a[contains(@aria-label, 'Next') or contains(@aria-label, 'التالي')] "
            "| //nav[@aria-label='Search results navigation']//a[last()] "
            "| //a[@aria-label='Next' or @aria-label='التالي']"
        )
        # الضغط باستخدام JavaScript لضمان التنفيذ حتى لو كان هناك عنصر يعلوه
        driver.execute_script("arguments[0].click();", next_button)
        page += 1
        time.sleep(4)
    except Exception as e:
        print("تعذر العثور على زر الصفحة التالية، جاري المحاولة برقم الصفحة:", e)
        try:
            target_page_btn = driver.find_element(By.XPATH, f"//nav//a[text()='{page + 1}']")
            driver.execute_script("arguments[0].click();", target_page_btn)
            page += 1
            time.sleep(4)
        except Exception:
            break

final_urls = list(listing_urls)[:50]
print(f"تم الانتهاء! العدد النهائي: {len(final_urls)}")
driver.quit()