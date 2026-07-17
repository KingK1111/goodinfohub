# 정보 허브 (info-hub)

부동산 경매 / META 주식 뉴스 / 단타 스크리너 정보를 자동으로 수집해 보여주는 정적 웹사이트입니다.
GitHub Actions가 주기적으로 데이터를 수집해 `data/*.json`을 갱신하고, GitHub Pages가 그 결과를 정적 페이지로 서빙합니다.

## 구성

- `index.html`, `assets/` — 정적 프론트엔드 (빌드 과정 없음, 순수 HTML/CSS/JS)
- `data/*.json` — 스크립트가 생성하는 최신 데이터 (커밋되어 사이트에 그대로 반영됨)
- `scripts/` — 데이터 수집 스크립트
  - `auctions_scraper.py`: 법원경매정보(courtauction.go.kr)에서 성동구/중구/동대문구/광진구/송파구 아파트 경매 물건 수집 (Selenium)
  - `meta_news_scraper.py`: META 주식 시세(Yahoo Finance) + 관련 뉴스(Google News RSS)
  - `stock_screener.py`: Yahoo Finance의 `day_gainers` / `most_actives` 스크리너를 조합해 거래량·변동성 상위 종목을 추림
- `.github/workflows/update-data.yml` — 하루 3회(08:00, 14:00, 20:00 KST) 자동 실행 + 수동 실행(workflow_dispatch)

## 로컬에서 실행

```bash
pip install -r scripts/requirements.txt
python scripts/auctions_scraper.py    # Chrome 필요 (Selenium)
python scripts/meta_news_scraper.py
python scripts/stock_screener.py
```

정적 사이트만 미리보려면:

```bash
python -m http.server 8000
# http://localhost:8000 접속
```
(fetch로 JSON을 불러오기 때문에 `file://`로 직접 열면 CORS로 인해 로드되지 않습니다.)

## GitHub Pages 배포 (최초 1회 수동 설정)

1. 이 폴더를 GitHub 저장소로 push
2. 저장소 Settings → Pages → Source를 `Deploy from a branch`, Branch를 `main` / `(root)`로 설정
3. 이후에는 Actions가 데이터를 갱신할 때마다 Pages가 자동으로 최신 내용을 반영합니다

## 참고 / 한계

- 법원경매정보 사이트 구조가 바뀌면 크롤러가 깨질 수 있습니다. 그 경우 `--show-browser` 옵션으로 브라우저를 띄워 디버깅하세요.
- 단타 스크리너는 공개 시세 데이터(거래량, 변동률)를 기준으로 자동 정렬한 참고 자료이며, 특정 종목의 매수/매도를 추천하지 않습니다. 투자 판단과 책임은 본인에게 있습니다.
