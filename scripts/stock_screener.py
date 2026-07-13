# -*- coding: utf-8 -*-
"""
단타(데이트레이딩) 후보 종목 스크리너.

Yahoo Finance의 사전 정의된 스크리너(day_gainers, most_actives)를 조합해
"거래량 급증" + "장중 변동성"이 큰 유동성 있는 종목을 뽑아 data/stocks.json 으로 저장한다.

주의: 이 스크립트는 공개 시세 데이터를 기준으로 자동 정렬/필터링만 수행하며,
매수/매도를 추천하지 않는다. 결과에는 항상 면책 문구가 포함된다.
"""
import json
import os
from datetime import datetime, timezone, timedelta

import yfinance as yf

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "stocks.json")

KST = timezone(timedelta(hours=9))

SCREENS = ["day_gainers", "most_actives"]
MIN_PRICE = 5.0
MIN_AVG_VOLUME = 500_000
TOP_N = 15

DISCLAIMER = (
    "이 목록은 공개 시세 데이터(거래량, 변동률)를 기준으로 자동 정렬한 결과이며 "
    "특정 종목의 매수/매도를 추천하지 않습니다. 투자 판단과 책임은 본인에게 있습니다."
)


def _fmt_reason(q, sources):
    change_pct = q.get("regularMarketChangePercent")
    rel_vol = q.get("relative_volume")
    parts = []
    if change_pct is not None:
        direction = "상승" if change_pct >= 0 else "하락"
        parts.append(f"장중 {change_pct:+.1f}% {direction}")
    if rel_vol is not None:
        parts.append(f"거래량 3개월 평균 대비 {rel_vol:.1f}배")
    if "most_actives" in sources:
        parts.append("거래대금 상위 종목")
    return ", ".join(parts) if parts else "변동성/거래량 기준 상위 종목"


def fetch_candidates():
    by_symbol = {}
    for screen_id in SCREENS:
        try:
            res = yf.screen(screen_id, count=50)
        except Exception:
            continue
        for q in res.get("quotes", []):
            symbol = q.get("symbol")
            if not symbol:
                continue
            price = q.get("regularMarketPrice")
            avg_vol = q.get("averageDailyVolume3Month")
            if price is None or avg_vol is None:
                continue
            if price < MIN_PRICE or avg_vol < MIN_AVG_VOLUME:
                continue
            entry = by_symbol.setdefault(symbol, {"quote": q, "sources": set()})
            entry["sources"].add(screen_id)

    candidates = []
    for symbol, entry in by_symbol.items():
        q = entry["quote"]
        volume = q.get("regularMarketVolume") or 0
        avg_vol = q.get("averageDailyVolume3Month") or 1
        relative_volume = volume / avg_vol
        q["relative_volume"] = relative_volume
        change_pct = q.get("regularMarketChangePercent") or 0
        score = abs(change_pct) * relative_volume
        candidates.append({
            "symbol": symbol,
            "name": q.get("shortName") or q.get("displayName"),
            "price": q.get("regularMarketPrice"),
            "change_percent": round(change_pct, 2),
            "volume": volume,
            "avg_volume_3m": int(avg_vol),
            "relative_volume": round(relative_volume, 2),
            "market_cap": q.get("marketCap"),
            "exchange": q.get("fullExchangeName"),
            "sources": sorted(entry["sources"]),
            "reason": _fmt_reason(q, entry["sources"]),
            "score": round(score, 2),
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:TOP_N]


def main():
    candidates = fetch_candidates()

    payload = {
        "updated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "disclaimer": DISCLAIMER,
        "criteria": {
            "min_price": MIN_PRICE,
            "min_avg_volume_3m": MIN_AVG_VOLUME,
            "sources": SCREENS,
        },
        "candidates": candidates,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"후보 {len(candidates)}종목 -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
