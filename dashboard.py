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

# ─── Terminal palette (Godel / Bloomberg-inspired) ──────────────────────────
BG          = "#0a0a0a"
PANEL       = "#111111"
PANEL_ALT   = "#161616"
BORDER      = "#2a2a2a"
BORDER_HOT  = "#3a3a3a"
TEXT        = "#e6e6e6"
TEXT_DIM    = "#8a8a8a"
TEXT_MUTED  = "#5a5a5a"
AMBER       = "#ffa500"
AMBER_SOFT  = "#cc8400"
CYAN        = "#5ec8ff"
GREEN       = "#22c55e"
RED         = "#ef4444"
PURPLE      = "#c084fc"
YELLOW      = "#facc15"
MONO        = "'JetBrains Mono','IBM Plex Mono','Fira Code',Menlo,Consolas,monospace"


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
    colors = {"SEC EDGAR": PURPLE, "News": CYAN, "Holdings Monitor": GREEN}
    color = colors.get(source, AMBER)
    return (
        f'<span style="border:1px solid {color};color:{color};background:transparent;'
        f'padding:1px 8px;font-size:10px;font-weight:700;letter-spacing:1.2px;'
        f'text-transform:uppercase;font-family:{MONO}">{html.escape(source)}</span>'
    )


def _significance_label(sig: str) -> str:
    labels = {
        "high":   ("PURE",     GREEN),
        "medium": ("NOTABLE",  YELLOW),
        "low":    ("INDIRECT", CYAN),
    }
    text, color = labels.get(sig, ("--", TEXT_MUTED))
    return (
        f'<span style="border:1px solid {color};color:{color};padding:1px 7px;'
        f'font-size:10px;font-weight:700;letter-spacing:1px;font-family:{MONO}">{text}</span>'
    )


def _holdings_breakdown(stock: dict) -> str:
    pct = stock.get("holdings_pct", {})
    if not pct:
        return html.escape(", ".join(stock.get("holdings", [])))
    parts = [
        f"<span style='color:{AMBER}'>{html.escape(k)}</span>"
        f"&nbsp;<span style='color:{TEXT_DIM}'>{html.escape(v)}</span>"
        for k, v in pct.items()
    ]
    return f" <span style='color:{TEXT_MUTED}'>|</span> ".join(parts)


def _watchlist_html() -> str:
    rows = []
    for s in KNOWN_HOLDING_STOCKS:
        ticker = s["ticker"]
        d = _live_price(ticker)
        if d:
            color = GREEN if d["pct"] >= 0 else RED
            arrow = "&#9650;" if d["pct"] >= 0 else "&#9660;"
            price_cell  = f'<span style="color:{TEXT}">${d["price"]:,.2f}</span>'
            change_cell = f'<span style="color:{color}">{arrow} {abs(d["pct"]):.2f}%</span>'
        else:
            price_cell  = f'<span style="color:{TEXT_MUTED}">--</span>'
            change_cell = f'<span style="color:{TEXT_MUTED}">--</span>'

        yf_url    = f"https://finance.yahoo.com/quote/{ticker}"
        sig_label = _significance_label(s.get("stake_significance", "low"))
        breakdown = _holdings_breakdown(s)
        desc      = html.escape(s.get("description", ""))

        rows.append(f"""
          <tr style="border-bottom:1px solid {BORDER}">
            <td style="padding:10px 12px;vertical-align:top;white-space:nowrap">
              <a href="{yf_url}" target="_blank"
                 style="font-weight:700;color:{AMBER};font-size:14px;text-decoration:none;letter-spacing:.5px">{ticker}</a><br>
              <span style="font-size:11px;color:{TEXT_DIM}">{html.escape(s['name'])}</span>
            </td>
            <td style="padding:10px 12px;vertical-align:top;font-size:14px;font-weight:600;white-space:nowrap">{price_cell}</td>
            <td style="padding:10px 12px;vertical-align:top;font-size:14px;white-space:nowrap">{change_cell}</td>
            <td style="padding:10px 12px;vertical-align:top">{sig_label}</td>
            <td style="padding:10px 12px;vertical-align:top;font-size:12px;line-height:1.7;color:{TEXT}">
              {breakdown}<br>
              <span style="color:{TEXT_MUTED};font-size:11px">{desc}</span>
            </td>
          </tr>""")

    if not rows:
        return '<p class="empty">// no stocks configured</p>'
    return f"""
      <table style="width:100%;border-collapse:collapse;font-family:{MONO}">
        <thead><tr style="font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:{AMBER};border-bottom:1px solid {AMBER_SOFT}">
          <th style="padding:8px 12px;text-align:left;font-weight:700">Ticker</th>
          <th style="padding:8px 12px;text-align:left;font-weight:700">Last</th>
          <th style="padding:8px 12px;text-align:left;font-weight:700">Chg %</th>
          <th style="padding:8px 12px;text-align:left;font-weight:700">Type</th>
          <th style="padding:8px 12px;text-align:left;font-weight:700">Holdings</th>
        </tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>"""


def _opportunity_cards(opps: list[dict], source_filter: str) -> str:
    filtered = [o for o in opps if o["source"] == source_filter]
    if not filtered:
        return '<p class="empty">// nothing found yet — check back after the next run</p>'
    cards = []
    for o in filtered:
        ts = o.get("discovered_at", "")[:16].replace("T", " ") + " UTC"
        company = html.escape(o.get("matched_company") or "")
        title = html.escape(o.get("title") or "")
        explanation = o.get("explanation") or ""
        link = o.get("link") or "#"
        company_pill = (
            f'<span style="border:1px solid {AMBER};color:{AMBER};padding:1px 8px;'
            f'font-size:10px;font-weight:700;letter-spacing:1px;font-family:{MONO}">{company}</span>'
            if company else ""
        )
        cards.append(f"""
        <div style="background:{PANEL_ALT};border:1px solid {BORDER};border-left:3px solid {AMBER};padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap">
            {_badge(source_filter)}
            {company_pill}
            <span style="margin-left:auto;font-size:11px;color:{TEXT_MUTED};font-family:{MONO}">{ts}</span>
          </div>
          <h3 style="margin:0 0 8px;font-size:14px;color:{TEXT};font-weight:600;letter-spacing:.2px">{title}</h3>
          <p style="margin:0 0 10px;font-size:13px;line-height:1.65;color:{TEXT_DIM}">{explanation}</p>
          <a href="{html.escape(link)}" target="_blank"
             style="color:{AMBER};font-size:11px;font-weight:700;text-decoration:none;
                    letter-spacing:1.5px;text-transform:uppercase;font-family:{MONO};
                    border-bottom:1px solid {AMBER_SOFT};padding-bottom:1px">
            &gt; view source
          </a>
        </div>""")
    return "".join(cards)


def _target_pills() -> str:
    pills = []
    for co in TARGET_COMPANIES:
        val = COMPANY_VALUATIONS.get(co, "")
        pills.append(
            f'<span style="border:1px solid {BORDER_HOT};background:{PANEL_ALT};color:{TEXT};'
            f'padding:5px 11px;font-size:12px;font-weight:600;font-family:{MONO};letter-spacing:.3px">'
            f'{html.escape(co)} <span style="color:{AMBER};margin-left:4px">{val}</span></span>'
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
  <title>IPO-NOTIF // Terminal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ background: {BG}; color: {TEXT}; }}
    body {{
      font-family: {MONO};
      font-size: 13px;
      line-height: 1.55;
      padding: 20px;
      background-image:
        radial-gradient(circle at 0% 0%, rgba(255,165,0,0.04), transparent 40%),
        radial-gradient(circle at 100% 100%, rgba(94,200,255,0.03), transparent 40%);
      min-height: 100vh;
    }}
    .wrap {{ max-width: 1180px; margin: 0 auto; }}
    a {{ color: {AMBER}; }}

    /* Top status bar */
    .topbar {{
      display: flex; justify-content: space-between; align-items: center;
      border: 1px solid {BORDER};
      background: {PANEL};
      padding: 6px 14px;
      font-size: 11px;
      color: {TEXT_DIM};
      letter-spacing: 1px;
      text-transform: uppercase;
      margin-bottom: 14px;
    }}
    .topbar .live {{ color: {GREEN}; }}
    .topbar .live::before {{
      content:"●"; color:{GREEN}; margin-right:6px;
      animation: blink 1.6s infinite;
    }}
    @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:.35}} }}

    /* Header banner */
    header {{
      border: 1px solid {BORDER};
      background: {PANEL};
      padding: 22px 26px;
      margin-bottom: 16px;
      position: relative;
      overflow: hidden;
    }}
    header::before {{
      content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
      background: {AMBER};
    }}
    header h1 {{
      font-size: 22px; font-weight: 700; color: {AMBER};
      letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px;
    }}
    header h1 .cursor {{
      display:inline-block; width:10px; height:18px; background:{AMBER};
      vertical-align:-2px; margin-left:4px; animation: blink 1.05s steps(2) infinite;
    }}
    header .sub {{
      color: {TEXT_DIM}; font-size: 12px; line-height: 1.7;
    }}
    header .sub strong {{ color: {TEXT}; font-weight: 600; }}
    header .meta {{
      display:flex; gap:18px; flex-wrap:wrap; margin-top: 12px;
      padding-top: 12px; border-top: 1px solid {BORDER};
      font-size: 11px; letter-spacing: 1px; text-transform: uppercase;
    }}
    header .meta .k {{ color: {TEXT_MUTED}; margin-right: 6px; }}
    header .meta .v {{ color: {AMBER}; font-weight: 700; }}

    section {{
      background: {PANEL};
      border: 1px solid {BORDER};
      padding: 18px 22px;
      margin-bottom: 14px;
    }}
    section h2 {{
      font-size: 12px;
      color: {AMBER};
      letter-spacing: 2px;
      text-transform: uppercase;
      padding-bottom: 10px;
      border-bottom: 1px solid {BORDER_HOT};
      margin-bottom: 14px;
      font-weight: 700;
      display:flex; align-items:center; gap:8px;
    }}
    section h2::before {{
      content: "▌"; color: {AMBER}; font-size: 14px;
    }}
    section .desc {{
      font-size: 12px; color: {TEXT_DIM}; margin-bottom: 14px; line-height: 1.7;
    }}
    section .desc strong.g {{ color: {GREEN}; }}
    section .desc strong.y {{ color: {YELLOW}; }}
    section .desc strong.c {{ color: {CYAN}; }}

    .pills {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .empty {{
      color: {TEXT_MUTED}; font-style: normal; padding: 6px 0;
      font-size: 12px; font-family: {MONO};
    }}

    footer {{
      text-align: center;
      font-size: 10px;
      color: {TEXT_MUTED};
      margin-top: 22px;
      padding: 14px 0;
      border-top: 1px solid {BORDER};
      letter-spacing: 1.5px;
      text-transform: uppercase;
    }}
    footer .sep {{ color: {BORDER_HOT}; margin: 0 8px; }}

    ::selection {{ background: {AMBER}; color: {BG}; }}
    ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
    ::-webkit-scrollbar-track {{ background: {BG}; }}
    ::-webkit-scrollbar-thumb {{ background: {BORDER_HOT}; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {AMBER_SOFT}; }}

    @media(max-width:640px) {{
      body {{ padding: 10px; font-size: 12px; }}
      header {{ padding: 16px; }}
      header h1 {{ font-size: 18px; letter-spacing: 1.5px; }}
      section {{ padding: 14px; }}
      .topbar {{ font-size: 10px; padding: 5px 10px; }}
    }}
  </style>
</head>
<body>
<div class="wrap">

  <div class="topbar">
    <span><span class="live">live</span> ipo-notif // v1.0</span>
    <span>{now}</span>
  </div>

  <header>
    <h1>IPO &amp; Investment Watchlist<span class="cursor"></span></h1>
    <p class="sub">Tracks publicly traded companies and funds that hold stakes in high-value private unicorns.<br>
       Auto-refresh every <strong>30 min</strong> &mdash; signal pulled from SEC EDGAR, Google News &amp; Yahoo Finance.</p>
    <div class="meta">
      <span><span class="k">last_run</span><span class="v">{now}</span></span>
      <span><span class="k">opportunities</span><span class="v">{total}</span></span>
      <span><span class="k">window</span><span class="v">60d</span></span>
      <span><span class="k">status</span><span class="v" style="color:{GREEN}">OK</span></span>
    </div>
  </header>

  <section>
    <h2>Tracking</h2>
    <div class="pills">{targets}</div>
  </section>

  <section>
    <h2>Public Holding Stocks &mdash; Live Quotes</h2>
    <p class="desc">
      <strong class="g">PURE</strong> = private stakes are most of the stock's value
      &nbsp;|&nbsp; <strong class="y">NOTABLE</strong> = meaningful exposure
      &nbsp;|&nbsp; <strong class="c">INDIRECT</strong> = large company, small relative stake
    </p>
    {watchlist}
  </section>

  <section>
    <h2>SEC Filings</h2>
    <p class="desc">
      New S-1 (IPO registrations), 13F (institutional holdings), and SC 13G/D filings that mention a target company.
    </p>
    {sec_cards}
  </section>

  <section>
    <h2>News Mentions</h2>
    <p class="desc">
      News articles referencing a target company alongside IPO / fund / stake keywords.
    </p>
    {news_cards}
  </section>

  <section>
    <h2>Holdings Stock Alerts</h2>
    <p class="desc">
      Recorded when a known holding stock moved &gt; 5% or saw 2.5&times; normal volume.
    </p>
    {alert_cards}
  </section>

  <footer>
    IPO-NOTIF<span class="sep">//</span>SEC EDGAR<span class="sep">//</span>GOOGLE NEWS<span class="sep">//</span>YAHOO FINANCE<span class="sep">//</span>NOT FINANCIAL ADVICE
  </footer>
</div>
</body>
</html>"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(html_out)
