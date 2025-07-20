#!/usr/bin/env python3
import re
import time
import sys
import requests
import mysql.connector
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import quote_plus

# ----------------------------
# CONFIGURATION
# ----------------------------
DB_CONFIG = {
    'host':     'localhost',
    'user':     'root',
    'password': 'root',
    'database': 'mcd_kualalumpur'
}
GOOGLE_MAPS_SEARCH = 'https://www.google.com/maps/search/'
NOMINATIM_URL      = 'https://nominatim.openstreetmap.org/search'
PHOTON_URL         = 'https://photon.komoot.io/api/'
HEADERS            = {'User-Agent': 'mcd-scraper/selenium/1.0'}
PAUSE_OSM          = 1.0    # seconds between Nominatim/Photon calls
BAR_LEN            = 40     # ASCII progress bar width

# ----------------------------
# HELPERS
# ----------------------------
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def clean_address(name: str, raw: str) -> str:
    """
    Strip Lot/Unit/Level, prepend name, append ', Malaysia'.
    """
    a = f"{name}, {raw}".strip()
    a = re.sub(
        r'^(.*?,\s*)(?:Lot[^,]+,|Unit[^,]+,|Level[^,]+,)\s*',
        r'\1',
        a,
        flags=re.IGNORECASE
    )
    a = re.sub(r'\s+', ' ', a)
    if not a.lower().endswith('malaysia'):
        a = a.rstrip('.,') + ', Malaysia'
    return a

def geocode_nominatim(address: str) -> tuple[float, float] | tuple[None, None]:
    """Try Nominatim first."""
    time.sleep(PAUSE_OSM)
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={'q': address, 'format': 'json', 'limit': 1, 'countrycodes': 'my'},
            headers=HEADERS,
            timeout=5
        )
        data = resp.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass
    return None, None

def geocode_photon(address: str) -> tuple[float, float] | tuple[None, None]:
    """Try Photon as fallback."""
    time.sleep(PAUSE_OSM)
    try:
        resp = requests.get(PHOTON_URL, params={'q': address, 'limit': 1}, timeout=5)
        feats = resp.json().get('features', [])
        if feats:
            lon, lat = feats[0]['geometry']['coordinates']
            return float(lat), float(lon)
    except Exception:
        pass
    return None, None

def geocode_with_selenium(address: str, driver) -> tuple[float, float] | tuple[None, None]:
    """
    Google Maps via Selenium.
    Open search URL, wait for redirect, parse @lat,lon from URL.
    """
    try:
        url = GOOGLE_MAPS_SEARCH + quote_plus(address)
        driver.get(url)
        # wait for redirect/page load
        time.sleep(5)
        final_url = driver.current_url
        m = re.search(r'/@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
        if m:
            return float(m.group(1)), float(m.group(2))
    except Exception:
        pass
    return None, None

def print_progress(idx, total, name, source, updated):
    pct = idx / total
    filled = int(BAR_LEN * pct)
    bar = '█' * filled + '-' * (BAR_LEN - filled)
    sys.stdout.write(
        f"\r[{bar}] {pct*100:5.1f}% ({idx}/{total}) "
        f"{name[:30]:30s} → {source:6s} | Updated: {updated}"
    )
    sys.stdout.flush()

# ----------------------------
# MAIN
# ----------------------------
def main():
    # Set up Selenium headless Chrome
    chrome_opts = Options()
    chrome_opts.add_argument('--headless')
    chrome_opts.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=chrome_opts)

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT id, name, address
          FROM outlets
         WHERE latitude IS NULL OR longitude IS NULL
    """)
    rows = cur.fetchall()
    total = len(rows)
    updated = 0

    UPDATE_SQL = """
        UPDATE outlets
           SET latitude = %s,
               longitude = %s
         WHERE id = %s
    """

    for idx, row in enumerate(rows, start=1):
        oid, name, raw = row['id'], row['name'], row['address'] or ''
        address = clean_address(name, raw)

        # 1) Nominatim
        lat, lon = geocode_nominatim(address)
        source = 'Nomin'

        # 2) Photon
        if lat is None:
            lat, lon = geocode_photon(address)
            source = 'Photon'

        # 3) Google Maps (Selenium)
        if lat is None:
            lat, lon = geocode_with_selenium(address, driver)
            source = 'GMap'

        if lat is not None and lon is not None:
            cur.execute(UPDATE_SQL, (lat, lon, oid))
            conn.commit()
            updated += 1

        print_progress(idx, total, name, source if lat else 'MISS', updated)

    print("\n[INFO] Geocoding complete.")
    driver.quit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
