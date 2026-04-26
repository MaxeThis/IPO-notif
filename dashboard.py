"""
Generates docs/index.html — a static dashboard served via GitHub Pages.
Runs at the end of every monitor cycle.
"""
import html
import os
from datetime import datetime

import requests

import database
from config import TARGET_COMPANIES, COMPANY_VALUATIONS, KNOWN_HOLDING_STOCKS
from analyzer import explain_sec_filing, explain_news_article, explain_holdings_alert

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
OUTPUT_PATH = os.path.join(DOCS_DIR, "index.html")

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; IPO-Notif/1.0)", "Accept": "application/json"}


def _live_price(ticker: str) -> dict | None:
    try:
        resp = requests.get(
            YAHOO_CHART_URL.format(ticker=ticker),
            params={"interval": "1d", "range": "5d"},
            headers=HEADERS, timeout=10,
        )
        resp.raise_for_status()
        result = resp.json().get("chart", {}).get("result", [])
        if not result:
            return None
        quotes = result[0].get("indicators", {}).get("quote", [{}])[0]
        closes = [c for c in quotes.get("close", []) if c is not None]
        volumes = [v for v in quotes.get("volume", []) if v is not None]
        if len(closes) < 2:
            return None
        pct = (closes[-1] - closes[-2]) / closes[-2] * 100
        return {"price": round(closes[-1], 2), "pct": round(pct, 2), "volume": volumes[-1] if volumes else 0}
    except Exception:
        return None


def _badge(source: str) -> str:
    colors = {"SEC EDGAR": "#7c3aed", "News": "#0891b2", "Holdings Monitor": "#15803d"}
    color = colors.get(source, "#374151")
    return f'<span style="background:{color};color:#fff;padding:2px 9px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.5px">{html.escape(source)}</span>'


def _significance_label(sig: str) -> str:
    labels = {
        "high":   ("Pure play",  "#15803d", "#dcfce7"),
        "medium": ("Notable",    "#92400e", "#fef3c7"),
        "low":    ("Indirect",   "#1e40af", "#eff6ff"),
    }
    text, fg, bg = labels.get(sig, ("—", "#6b7280", "#f3f4f6"))
    return f'<span style="background:{bg};color:{fg};padding:1px 7px;border-radius:999px;font-size:11px;font-weight:600">{text}</span>'


def _holdings_breakdown(stock: dict) -> str:
    pct = stock.get("holdings_pct", {})
    if not pct:
        return html.escape(", ".join(stock.get("holdings", [])))
    parts = [f"<strong>{html.escape(k)}</strong>&nbsp;<span style='color:#6b7280'>{html.escape(v)}</span>"
             for k, v in pct.items()]
    return " &nbsp;·&nbsp; ".join(parts)


def _watchlist_html() -> str:
    rows = []
    for s in KNOWN_HOLDING_STOCKS:
        ticker = s["ticker"]
        d = _live_price(ticker)
        if d:
            color = "#16a34a" if d["pct"] >= 0 else "#dc2626"
            arrow = "&#9650;" if d["pct"] >= 0 else "&#9660;"
            price_cell  = f"${d['price']:,.2f}"
            change_cell = f'<span style="color:{color}">{arrow} {abs(d["pct"]):.2f}%</span>'
        else:
            price_cell  = '<span style="color:#9ca3af">—</span>'
            change_cell = '<span style="color:#9ca3af">—</span>'

        yf_url    = f"https://finance.yahoo.com/quote/{ticker}"
        sig_label = _significance_label(s.get("stake_significance", "low"))
        breakdown = _holdings_breakdown(s)
        desc      = html.escape(s.get("description", ""))

        rows.append(f"""
          <tr style="border-bottom:1px solid #f3f4f6">
            <td style="padding:14px 12px;vertical-align:top">
              <a href="{yf_url}" target="_blank"
                 style="font-weight:700;color:#2563eb;font-size:15px">{ticker}</a><br>
              <span style="font-size:12px;color:#6b7280">{html.escape(s['name'])}</span>
            </td>
            <td style="padding:14px 12px;vertical-align:top;font-size:15px;font-weight:600">{price_cell}</td>
            <td style="padding:14px 12px;vertical-align:top;font-size:15px">{change_cell}</td>
            <td style="padding:14px 12px;vertical-align:top">{sig_label}</td>
            <td style="padding:14px 12px;vertical-align:top;font-size:13px;line-height:1.8">
              {breakdown}<br>
              <span style="color:#9ca3af;font-size:12px">{desc}</span>
            </td>
          </tr>""")

    if not rows:
        return '<p class="empty">No stocks configured.</p>'
    return f"""
      <table style="width:100%;border-collapse:collapse">
        <thead><tr style="font-size:11px;text-transform:uppercase;color:#9ca3af;border-bottom:2px solid #e5e7eb">
          <th style="padding:8px 12px;text-align:left">Ticker</th>
          <th style="padding:8px 12px;text-align:left">Price</th>
          <th style="padding:8px 12px;text-align:left">Today</th>
          <th style="padding:8px 12px;text-align:left">Type</th>
          <th style="padding:8px 12px;text-align:left">Holdings Breakdown</th>
        </tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>"""


def _opportunity_cards(opps: list[dict], source_filter: str) -> str:
    filtered = [o for o in opps if o["source"] == source_filter]
    if not filtered:
        return '<p class="empty">Nothing found yet — check back after the next run.</p>'
    cards = []
    for o in filtered:
        ts = o.get("discovered_at", "")[:16].replace("T", " ") + " UTC"
        company = html.escape(o.get("matched_company") or "")
        title = html.escape(o.get("title") or "")
        explanation = o.get("explanation") or ""
        link = o.get("link") or "#"
        cards.append(f"""
        <div style="background:#f9fafb;border-left:4px solid #2563eb;padding:16px 18px;margin-bottom:14px;border-radius:6px">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            {_badge(source_filter)}
            {f'<span style="background:#eff6ff;color:#1e40af;padding:2px 9px;border-radius:999px;font-size:11px;font-weight:600">{company}</span>' if company else ''}
          </div>
          <h3 style="margin:0 0 4px;font-size:15px;color:#111827">{title}</h3>
          <p style="margin:0 0 10px;font-size:12px;color:#9ca3af">{ts}</p>
          <p style="margin:0 0 12px;font-size:14px;line-height:1.65;color:#374151">{explanation}</p>
          <a href="{html.escape(link)}" target="_blank"
             style="color:#2563eb;font-size:13px;font-weight:600;text-decoration:none">
            View source &#8594;
          </a>
        </div>""")
    return "".join(cards)


def _target_pills() -> str:
    pills = []
    for co in TARGET_COMPANIES:
        val = COMPANY_VALUATIONS.get(co, "")
        pills.append(
            f'<span style="background:#eff6ff;color:#1e40af;padding:6px 14px;'
            f'border-radius:999px;font-size:13px;font-weight:500">'
            f'{html.escape(co)} <span style="opacity:.65">{val}</span></span>'
        )
    return "".join(pills)


def generate() -> None:
    os.makedirs(DOCS_DIR, exist_ok=True)
    opps = database.get_recent_opportunities(days=60)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    total = len(opps)

    sec_cards   = _opportunity_cards(opps, "SEC EDGAR")
    news_cards  = _opportunity_cards(opps, "News")
    alert_cards = _opportunity_cards(opps, "Holdings Monitor")
    watchlist   = _watchlist_html()
    targets     = _target_pills()

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="refresh" content="1800">
  <title>IPO &amp; Investment Watchlist</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: #f3f4f6; color: #111827; padding: 24px; }}
    .wrap {{ max-width: 1000px; margin: 0 auto; }}
    header {{ background: linear-gradient(135deg,#1e3a5f,#2563eb); color: #fff;
              padding: 32px 28px; border-radius: 14px; margin-bottom: 24px; }}
    header h1 {{ font-size: 26px; margin-bottom: 8px; }}
    header p  {{ opacity: .8; font-size: 14px; line-height: 1.6; }}
    section {{ background: #fff; border-radius: 12px; padding: 24px;
               margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }}
    section h2 {{ font-size: 18px; color: #1e3a5f; padding-bottom: 12px;
                  border-bottom: 2px solid #e5e7eb; margin-bottom: 18px; }}
    .pills {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .empty {{ color: #9ca3af; font-style: italic; padding: 8px 0; font-size: 14px; }}
    footer {{ text-align: center; font-size: 12px; color: #9ca3af; margin-top: 32px; }}
    @media(max-width:600px) {{ body {{ padding: 12px; }} header {{ padding: 20px; }} }}
  </style>
</head>
<body>
<div class="wrap">

  <header>
    <h1>&#128202; IPO &amp; Investment Watchlist</h1>
    <p>Tracks publicly traded companies and funds that hold stakes in high-value private unicorns.<br>
       Auto-updated every 30&nbsp;minutes &mdash; last run: <strong>{now}</strong>
       &nbsp;&bull;&nbsp; {total} opportunit{'y' if total==1 else 'ies'} recorded (last 60 days)</p>
  </header>

  <section>
    <h2>&#127919; Tracking</h2>
    <div class="pills">{targets}</div>
  </section>

  <section>
    <h2>&#128200; Public Holding Stocks &mdash; Live Prices</h2>
    <p style="font-size:13px;color:#6b7280;margin-bottom:16px">
      <strong style="color:#15803d">Pure play</strong> = private stakes are most of the stock's value &nbsp;·&nbsp;
      <strong style="color:#92400e">Notable</strong> = meaningful exposure &nbsp;·&nbsp;
      <strong style="color:#1e40af">Indirect</strong> = large company, small relative stake
    </p>
    {watchlist}
  </section>

  <section>
    <h2>&#128196; SEC Filings</h2>
    <p style="font-size:13px;color:#6b7280;margin-bottom:14px">
      New S-1 (IPO registrations), 13F (institutional holdings), and SC 13G/D filings
      that mention a target company.
    </p>
    {sec_cards}
  </section>

  <section>
    <h2>&#128240; News Mentions</h2>
    <p style="font-size:13px;color:#6b7280;margin-bottom:14px">
      News articles referencing a target company alongside IPO / fund / stake keywords.
    </p>
    {news_cards}
  </section>

  <section>
    <h2>&#128268; Holdings Stock Alerts</h2>
    <p style="font-size:13px;color:#6b7280;margin-bottom:14px">
      Recorded when a known holding stock moved &gt;5&nbsp;% or saw 2.5&times;&nbsp;normal volume.
    </p>
    {alert_cards}
  </section>

  <footer>IPO-Notif &bull; Data from SEC EDGAR, Google News, Yahoo Finance &bull; Not financial advice</footer>
</div>
</body>
</html>"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(html_out)
