#!/usr/bin/env python3
import re
import time
import json
import mysql.connector
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup

# ----------------------------
# DB CONFIG
# ----------------------------
db_config = {
    'host':     'localhost',
    'user':     'root',
    'password': 'root',
    'database': 'mcd_kualalumpur'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# ----------------------------
# SCRAPER SETUP
# ----------------------------
def init_driver():
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1920,1080')
    print("[INFO] Initializing headless Chrome driver...")
    driver = webdriver.Chrome(options=opts)
    print("[INFO] Driver initialized.")
    return driver

def perform_search(driver):
    driver.get('https://www.mcdonalds.com.my/locate-us')
    time.sleep(2)
    box = driver.find_element(By.ID, 'address')
    box.clear()
    box.send_keys('kuala lumpur')
    driver.find_element(By.CSS_SELECTOR, 'div.btnSearchNow').click()
    time.sleep(3)

def load_all_results(driver):
    page = 1
    while True:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, '.btnLoadMore')
            driver.execute_script("arguments[0].scrollIntoView();", btn)
            btn.click()
            time.sleep(2)
            page += 1
        except Exception:
            break

# ----------------------------
# PERKS HELPERS
# ----------------------------
def get_or_create_perk(conn, name: str):
    code = re.sub(r'[^A-Za-z0-9]+', '_', name.strip()).upper()
    cur = conn.cursor()
    cur.execute("SELECT id FROM perks WHERE code=%s", (code,))
    row = cur.fetchone()
    if row:
        pid = row[0]
    else:
        cur.execute("INSERT INTO perks (code, name) VALUES (%s, %s)", (code, name.strip()))
        conn.commit()
        pid = cur.lastrowid
    cur.close()
    return pid

def link_outlet_perks(conn, outlet_id: int, perk_ids: list):
    cur = conn.cursor()
    for pid in perk_ids:
        cur.execute("""
            INSERT IGNORE INTO outlet_perks (outlet_id, perk_id)
            VALUES (%s, %s)
        """, (outlet_id, pid))
    conn.commit()
    cur.close()

# ----------------------------
# SCRAPE & STORE
# ----------------------------
def save_outlet_and_perks(entry: dict):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO outlets
          (name, address, waze_link)
        VALUES (%s, %s, %s)
    """, (entry['name'], entry['address'], entry['waze_link']))
    conn.commit()
    outlet_id = cur.lastrowid
    cur.close()

    perk_ids = []
    for perk_name in entry['perks']:
        pid = get_or_create_perk(conn, perk_name)
        perk_ids.append(pid)

    link_outlet_perks(conn, outlet_id, perk_ids)
    conn.close()

    print(f"[INFO] Saved '{entry['name']}' with perks: {entry['perks']}")

def scrape_and_store(driver):
    cards = driver.find_elements(By.CSS_SELECTOR, 'div.columns.large-3.medium-4.small-12')
    original = driver.current_window_handle

    for idx, card in enumerate(cards, start=1):
        print(f"[INFO] Processing outlet {idx}/{len(cards)}...")
        html = card.get_attribute('innerHTML')
        soup = BeautifulSoup(html, 'html.parser')

        entry = {
            'name': None,
            'address': None,
            'waze_link': None,
            'perks': []
        }

        script = soup.find('script', type='application/ld+json')
        if script and script.string:
            data = json.loads(script.string)
            entry['name']    = data.get('name')
            entry['address'] = data.get('address')

        for span in soup.select('.addressTop .ed-tooltiptext'):
            text = span.get_text(strip=True)
            if text and 'caret' not in text.lower():
                entry['perks'].append(text)

        try:
            waze = card.find_element(By.XPATH, ".//a[contains(text(),'Waze')]")
            driver.execute_script("arguments[0].click();", waze)
            time.sleep(2)
            for h in driver.window_handles:
                if h != original:
                    driver.switch_to.window(h)
                    entry['waze_link'] = driver.current_url
                    driver.close()
                    driver.switch_to.window(original)
                    break
        except (NoSuchElementException, TimeoutException):
            pass

        save_outlet_and_perks(entry)

if __name__ == '__main__':
    driver = init_driver()
    try:
        perform_search(driver)
        load_all_results(driver)
        scrape_and_store(driver)
        print("[INFO] All done.")
    finally:
        driver.quit()
