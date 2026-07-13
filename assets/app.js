const TABS = ["auctions", "meta", "stocks"];

function fmtDate(iso) {
  if (!iso) return "업데이트 정보 없음";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" });
}

function fmtNumber(n) {
  if (n === null || n === undefined) return "-";
  return Number(n).toLocaleString("en-US");
}

function el(tag, opts = {}, children = []) {
  const node = document.createElement(tag);
  if (opts.className) node.className = opts.className;
  if (opts.text) node.textContent = opts.text;
  if (opts.html) node.innerHTML = opts.html;
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
  for (const c of children) node.appendChild(c);
  return node;
}

async function loadJSON(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} 로드 실패 (${res.status})`);
  return res.json();
}

function initTabs() {
  const buttons = document.querySelectorAll("nav.tabs button");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll("section.panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`panel-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

function renderAuctions(data) {
  const meta = document.getElementById("auctions-meta");
  meta.textContent = `업데이트: ${fmtDate(data.updated_at)} · 대상 지역: ${data.districts.join(", ")} · 총 ${data.items.length}건`;

  const container = document.getElementById("auctions-content");
  container.innerHTML = "";

  if (!data.items.length) {
    container.appendChild(el("div", { className: "empty-state", text: "표시할 경매 물건이 없습니다." }));
    return;
  }

  const byDistrict = {};
  for (const item of data.items) {
    (byDistrict[item.district] ||= []).push(item);
  }

  for (const district of data.districts) {
    const items = byDistrict[district];
    if (!items || !items.length) continue;
    const group = el("div", { className: "district-group" });
    group.appendChild(el("h3", { text: `${district} (${items.length}건)` }));
    for (const item of items) {
      const card = el("div", { className: "card" });
      card.appendChild(el("div", { className: "card-title", text: item.address || "-" }));
      const row1 = el("div", { className: "card-row" }, [
        el("span", { text: `사건번호: ${item.case_no}` }),
        el("span", { text: `용도: ${item.usage}` }),
        el("span", { className: "badge", text: item.status }),
      ]);
      const row2 = el("div", { className: "card-row" }, [
        el("span", { text: `감정가: ${item.appraisal_amount}원` }),
        el("span", { text: `최저매각가: ${item.min_sale_price}` }),
        el("span", { text: item.court_and_date }),
      ]);
      card.appendChild(row1);
      card.appendChild(row2);
      if (item.remarks) {
        card.appendChild(el("div", { className: "card-row", text: `비고: ${item.remarks}` }));
      }
      group.appendChild(card);
    }
    container.appendChild(group);
  }

  if (data.errors && data.errors.length) {
    const errBox = el("div", { className: "disclaimer" });
    errBox.textContent = `일부 지역 수집 실패: ${data.errors.join(" / ")}`;
    container.prepend(errBox);
  }
}

function renderMeta(data) {
  const meta = document.getElementById("meta-meta");
  meta.textContent = `업데이트: ${fmtDate(data.updated_at)}`;

  const quoteBox = document.getElementById("meta-quote");
  quoteBox.innerHTML = "";
  const q = data.quote;
  if (q && !q.error) {
    const isUp = (q.change_percent ?? 0) >= 0;
    quoteBox.appendChild(el("div", { className: "quote-price", text: `$${q.price ?? "-"}` }));
    quoteBox.appendChild(
      el("div", {
        className: `quote-change ${isUp ? "up" : "down"}`,
        text: `${isUp ? "+" : ""}${q.change ?? "-"} (${isUp ? "+" : ""}${q.change_percent ?? "-"}%)`,
      })
    );
    quoteBox.appendChild(
      el("div", { className: "section-meta", text: `일중 ${q.day_low ?? "-"} ~ ${q.day_high ?? "-"} · 시가총액 $${fmtNumber(Math.round((q.market_cap || 0) / 1e8) / 10)}B` })
    );
  } else {
    quoteBox.appendChild(el("div", { className: "empty-state", text: "시세 정보를 불러오지 못했습니다." }));
  }

  const list = document.getElementById("meta-news-list");
  list.innerHTML = "";
  if (!data.articles || !data.articles.length) {
    list.appendChild(el("div", { className: "empty-state", text: "표시할 뉴스가 없습니다." }));
    return;
  }
  for (const a of data.articles) {
    const card = el("div", { className: "card" });
    const link = el("a", { attrs: { href: a.link, target: "_blank", rel: "noopener noreferrer" }, text: a.title });
    card.appendChild(el("div", { className: "card-title" }, [link]));
    card.appendChild(
      el("div", { className: "card-row" }, [
        el("span", { text: a.source || "" }),
        el("span", { text: a.published || "" }),
      ])
    );
    list.appendChild(card);
  }
}

function renderStocks(data) {
  const meta = document.getElementById("stocks-meta");
  meta.textContent = `업데이트: ${fmtDate(data.updated_at)} · 기준: 최소가 $${data.criteria?.min_price ?? "-"}, 3개월 평균거래량 ${fmtNumber(data.criteria?.min_avg_volume_3m)}주 이상`;

  const disclaimer = document.getElementById("stocks-disclaimer");
  disclaimer.textContent = data.disclaimer || "";

  const container = document.getElementById("stocks-content");
  container.innerHTML = "";

  if (!data.candidates || !data.candidates.length) {
    container.appendChild(el("div", { className: "empty-state", text: "표시할 종목이 없습니다." }));
    return;
  }

  const wrap = el("div", { className: "table-wrap" });
  const table = el("table", { className: "stock-table" });
  const thead = el("thead", {}, [
    el("tr", {}, [
      el("th", { text: "종목" }),
      el("th", { text: "이름" }),
      el("th", { text: "현재가" }),
      el("th", { text: "등락률" }),
      el("th", { text: "거래량" }),
      el("th", { text: "상대거래량" }),
      el("th", { text: "설명" }),
    ]),
  ]);
  table.appendChild(thead);

  const tbody = el("tbody");
  for (const c of data.candidates) {
    const isUp = (c.change_percent ?? 0) >= 0;
    const tr = el("tr", {}, [
      el("td", { text: c.symbol }),
      el("td", { text: c.name || "-" }),
      el("td", { text: `$${c.price ?? "-"}` }),
      el("td", { className: isUp ? "change-up" : "change-down", text: `${isUp ? "+" : ""}${c.change_percent}%` }),
      el("td", { text: fmtNumber(c.volume) }),
      el("td", { text: `${c.relative_volume}x` }),
      el("td", { className: "reason", text: c.reason }),
    ]);
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
  container.appendChild(wrap);
}

async function main() {
  initTabs();

  try {
    renderAuctions(await loadJSON("data/auctions.json"));
  } catch (e) {
    document.getElementById("auctions-content").innerHTML = `<div class="empty-state">${e.message}</div>`;
  }

  try {
    renderMeta(await loadJSON("data/meta_news.json"));
  } catch (e) {
    document.getElementById("meta-news-list").innerHTML = `<div class="empty-state">${e.message}</div>`;
  }

  try {
    renderStocks(await loadJSON("data/stocks.json"));
  } catch (e) {
    document.getElementById("stocks-content").innerHTML = `<div class="empty-state">${e.message}</div>`;
  }
}

main();
