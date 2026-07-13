# -*- coding: utf-8 -*-
"""
메타(META) 주식 관련 최신 뉴스와 시세를 수집해 data/meta_news.json 으로 저장한다.
- 시세: yfinance (Yahoo Finance, API 키 불필요)
- 뉴스: Google News RSS 검색 (API 키 불필요)
"""
import json
import os
import urllib.parse
from datetime import datetime, timezone, timedelta

import feedparser
import yfinance as yf

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "meta_news.json")

KST = timezone(timedelta(hours=9))
NEWS_QUERY = "Meta Platforms META stock"
MAX_ARTICLES = 20


def fetch_quote():
    try:
        info = yf.Ticker("META").fast_info
        last = info.get("lastPrice")
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        change = None
        change_percent = None
        if last is not None and prev_close:
            change = last - prev_close
            change_percent = (change / prev_close) * 100
        return {
            "symbol": "META",
            "price": round(last, 2) if last is not None else None,
            "previous_close": round(prev_close, 2) if prev_close else None,
            "change": round(change, 2) if change is not None else None,
            "change_percent": round(change_percent, 2) if change_percent is not None else None,
            "currency": info.get("currency"),
            "day_high": info.get("dayHigh"),
            "day_low": info.get("dayLow"),
            "market_cap": info.get("marketCap"),
        }
    except Exception as exc:
        return {"error": str(exc)}


def fetch_articles():
    query = urllib.parse.quote(NEWS_QUERY)
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:MAX_ARTICLES]:
        articles.append({
            "title": entry.get("title"),
            "link": entry.get("link"),
            "source": entry.get("source", {}).get("title") if entry.get("source") else None,
            "published": entry.get("published"),
        })
    return articles


def main():
    payload = {
        "updated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "quote": fetch_quote(),
        "articles": fetch_articles(),
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"뉴스 {len(payload['articles'])}건 수집 -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
