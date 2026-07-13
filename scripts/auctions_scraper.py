# -*- coding: utf-8 -*-
"""
법원경매정보(courtauction.go.kr)에서 지정된 구(區)의 아파트 경매 물건을 수집해
data/auctions.json 으로 저장한다. GitHub Actions 등 headless 환경에서 실행되는 것을
전제로 Selenium Manager(내장, Selenium 4.6+)가 알아서 chromedriver를 받아오도록 한다.
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

SIDO = "서울특별시"
DISTRICTS = ["성동구", "중구", "동대문구", "광진구", "송파구"]

SEARCH_URL = (
    "https://www.courtauction.go.kr/pgj/index.on"
    "?w2xPath=%2Fpgj%2Fui%2Fpgj100%2FPGJ151F00.xml"
)
COLUMN_COUNT = 11

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "auctions.json")

KST = timezone(timedelta(hours=9))


def make_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1600,1200")
    opts.add_argument("--log-level=3")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)


def _js_select(driver, elem_id, value):
    driver.execute_script(
        """
        var el = document.getElementById(arguments[0]);
        el.value = arguments[1];
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new Event('input', {bubbles: true}));
        """,
        elem_id,
        value,
    )


def _js_click(driver, elem_id):
    driver.execute_script("document.getElementById(arguments[0]).click();", elem_id)


def _read_row(driver, row_idx):
    cells = []
    for col in range(COLUMN_COUNT):
        try:
            cell = driver.find_element(
                "id", f"mf_wfm_mainFrame_grd_gdsDtlSrchResult_cell_{row_idx}_{col}"
            )
            cells.append(" ".join(cell.text.split()))
        except Exception:
            return None
    return cells


def _row_to_listing(cells, district):
    case_no_display = cells[1]
    if not case_no_display:
        return None
    return {
        "district": district,
        "case_no": case_no_display,
        "item_no": cells[2],
        "address": cells[3],
        "remarks": cells[5],
        "appraisal_amount": cells[6],
        "court_and_date": cells[7],
        "usage": cells[8],
        "min_sale_price": cells[9],
        "status": cells[10],
    }


def search_district(driver, district):
    driver.get(SEARCH_URL)
    time.sleep(3)

    _js_click(driver, "mf_wfm_mainFrame_rad_rletSrchBtn_input_1")  # 소재지(지번주소) 검색
    time.sleep(1.2)
    _js_select(driver, "mf_wfm_mainFrame_sbx_rletAdongSdS", SIDO)
    time.sleep(1.2)
    _js_select(driver, "mf_wfm_mainFrame_sbx_rletAdongSggS", district)
    time.sleep(0.8)
    _js_select(driver, "mf_wfm_mainFrame_sbx_rletLclLst", "건물")
    time.sleep(0.8)
    _js_select(driver, "mf_wfm_mainFrame_sbx_rletMclLst", "주거용건물")
    time.sleep(0.8)
    _js_select(driver, "mf_wfm_mainFrame_sbx_rletSclLst", "아파트")
    time.sleep(0.8)

    driver.find_element("id", "mf_wfm_mainFrame_btn_gdsDtlSrch").click()
    time.sleep(4)

    listings = []
    row_idx = 0
    empty_streak = 0
    while empty_streak < 3 and row_idx < 300:
        cells = _read_row(driver, row_idx)
        if cells is None:
            empty_streak += 1
            row_idx += 1
            continue
        empty_streak = 0
        listing = _row_to_listing(cells, district)
        if listing:
            listings.append(listing)
        row_idx += 1
    return listings


def fetch_all(districts, headless=True):
    driver = make_driver(headless=headless)
    all_listings = []
    errors = []
    try:
        for district in districts:
            try:
                all_listings.extend(search_district(driver, district))
            except Exception as exc:  # keep going even if one district fails
                errors.append(f"{district}: {exc}")
    finally:
        driver.quit()
    return all_listings, errors


def main():
    parser = argparse.ArgumentParser(description="법원경매정보 아파트 경매 수집 -> JSON")
    parser.add_argument("--show-browser", action="store_true", help="크롬 창을 띄워서 실행 (디버그용)")
    parser.add_argument("--districts", nargs="*", default=DISTRICTS)
    args = parser.parse_args()

    listings, errors = fetch_all(args.districts, headless=not args.show_browser)

    payload = {
        "updated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "districts": args.districts,
        "items": listings,
        "errors": errors,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"{len(listings)}건 수집, {len(errors)}건 오류 -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
