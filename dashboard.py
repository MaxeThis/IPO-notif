"""
Generates docs/index.html — a static dashboard served via GitHub Pages.
Runs at the end of every monitor cycle.
"""
import html
import json
import os
from collections import Counter
from datetime import datetime

import requests

import database
from config import (
    TARGET_COMPANIES,
    COMPANY_VALUATIONS,
    KNOWN_HOLDING_STOCKS,
    UPCOMING_IPOS,
    DISCOVERY_HEURISTICS,
)

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
OUTPUT_PATH = os.path.join(DOCS_DIR, "index.html")

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
SUMMARY_URL = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; IPO-Notif/1.0)", "Accept": "application/json"}


def _live_quote(ticker: str) -> dict:
    """Fetch price + valuation metrics. Missing fields are returned as None."""
    out = {"price": None, "pct": None, "nav": None, "pe": None,
           "peg": None, "market_cap": None, "name": None}

    # Price + % change from the chart endpoint (reliable)
    try:
        r = requests.get(
            CHART_URL.format(ticker=ticker),
            params={"interval": "1d", "range": "5d"},
            headers=HEADERS, timeout=10,
        )
        r.raise_for_status()
        result = r.json().get("chart", {}).get("result", [])
        if result:
            quotes = result[0].get("indicators", {}).get("quote", [{}])[0]
            closes = [c for c in quotes.get("close", []) if c is not None]
            if len(closes) >= 2:
                out["price"] = round(closes[-1], 2)
                out["pct"] = round((closes[-1] - closes[-2]) / closes[-2] * 100, 2)
            elif closes:
                out["price"] = round(closes[-1], 2)
            meta = result[0].get("meta", {})
            out["name"] = meta.get("longName") or meta.get("shortName")
    except Exception:
        pass

    # PE / PEG / NAV / market cap from quoteSummary (best-effort; Yahoo may gate this)
    try:
        r = requests.get(
            SUMMARY_URL.format(ticker=ticker),
            params={"modules": "summaryDetail,defaultKeyStatistics,price"},
            headers=HEADERS, timeout=10,
        )
        if r.ok:
            res = r.json().get("quoteSummary", {}).get("result", [])
            if res:
                sd = res[0].get("summaryDetail", {}) or {}
                ks = res[0].get("defaultKeyStatistics", {}) or {}
                pr = res[0].get("price", {}) or {}

                def _num(field):
                    v = field or {}
                    return v.get("raw") if isinstance(v, dict) else None

                out["pe"] = _num(sd.get("trailingPE")) or _num(ks.get("trailingPE"))
                out["peg"] = _num(ks.get("pegRatio"))
                out["nav"] = _num(sd.get("navPrice")) or _num(ks.get("navPrice"))
                out["market_cap"] = _num(pr.get("marketCap")) or _num(sd.get("marketCap"))
                out["name"] = out["name"] or pr.get("longName") or pr.get("shortName")
    except Exception:
        pass

    return out


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


def _fmt(v, prefix="", suffix="", digits=2) -> str:
    if v is None:
        return '<span style="color:#9ca3af">—</span>'
    try:
        return f"{prefix}{float(v):,.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return f"{prefix}{v}{suffix}"


def _trading_table() -> str:
    rows = []
    for s in [x for x in KNOWN_HOLDING_STOCKS if x.get("status", "trading") == "trading"]:
        ticker = s["ticker"]
        d = _live_quote(ticker)
        if d["price"] is not None and d["pct"] is not None:
            color = "#16a34a" if d["pct"] >= 0 else "#dc2626"
            arrow = "&#9650;" if d["pct"] >= 0 else "&#9660;"
            price_cell = f'${d["price"]:,.2f}<br><span style="color:{color};font-size:12px">{arrow} {abs(d["pct"]):.2f}%</span>'
        elif d["price"] is not None:
            price_cell = f'${d["price"]:,.2f}'
        else:
            price_cell = '<span style="color:#9ca3af">—</span>'

        nav_cell = _fmt(d["nav"], prefix="$")
        pe_cell  = _fmt(d["pe"])
        peg_cell = _fmt(d["peg"])

        yf_url    = f"https://finance.yahoo.com/quote/{ticker}"
        sig_label = _significance_label(s.get("stake_significance", "low"))
        breakdown = _holdings_breakdown(s)
        desc      = html.escape(s.get("description", ""))

        rows.append(f"""
          <tr style="border-bottom:1px solid #f3f4f6">
            <td style="padding:14px 12px;vertical-align:top;min-width:120px">
              <a href="{yf_url}" target="_blank"
                 style="font-weight:700;color:#2563eb;font-size:15px">{ticker}</a><br>
              <span style="font-size:12px;color:#6b7280">{html.escape(s['name'])}</span>
            </td>
            <td style="padding:14px 12px;vertical-align:top;font-size:14px;font-weight:600">{price_cell}</td>
            <td style="padding:14px 12px;vertical-align:top;font-size:13px">{nav_cell}</td>
            <td style="padding:14px 12px;vertical-align:top;font-size:13px">{pe_cell}</td>
            <td style="padding:14px 12px;vertical-align:top;font-size:13px">{peg_cell}</td>
            <td style="padding:14px 12px;vertical-align:top">{sig_label}</td>
            <td style="padding:14px 12px;vertical-align:top;font-size:13px;line-height:1.7">
              {breakdown}<br>
              <span style="color:#9ca3af;font-size:12px">{desc}</span>
            </td>
          </tr>""")

    if not rows:
        return '<p class="empty">No trading stocks configured.</p>'
    return f"""
      <table style="width:100%;border-collapse:collapse">
        <thead><tr style="font-size:11px;text-transform:uppercase;color:#9ca3af;border-bottom:2px solid #e5e7eb">
          <th style="padding:8px 12px;text-align:left">Ticker</th>
          <th style="padding:8px 12px;text-align:left">Price / Today</th>
          <th style="padding:8px 12px;text-align:left">NAV</th>
          <th style="padding:8px 12px;text-align:left">P/E</th>
          <th style="padding:8px 12px;text-align:left">PEG</th>
          <th style="padding:8px 12px;text-align:left">Type</th>
          <th style="padding:8px 12px;text-align:left">Holdings</th>
        </tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>"""


def _upcoming_table() -> str:
    entries = list(UPCOMING_IPOS) + [x for x in KNOWN_HOLDING_STOCKS if x.get("status") == "upcoming"]
    if not entries:
        return ('<p class="empty">No upcoming IPOs in the watchlist yet. Add entries to '
                '<code>UPCOMING_IPOS</code> in <code>config.py</code> as filings are confirmed, '
                'or check the <em>Auto-discovered candidates</em> section below for new filers.</p>')

    rows = []
    for s in entries:
        ticker = s.get("ticker", "TBD")
        sig_label = _significance_label(s.get("stake_significance", "low"))
        breakdown = _holdings_breakdown(s)
        desc      = html.escape(s.get("description", ""))
        ipo_date  = html.escape(s.get("ipo_date", "TBD"))
        price     = html.escape(s.get("expected_price", "—"))
        proceeds  = html.escape(s.get("expected_proceeds", "—"))
        link      = s.get("filing_url") or (f"https://finance.yahoo.com/quote/{ticker}" if ticker != "TBD" else "#")
        ticker_html = (f'<a href="{html.escape(link)}" target="_blank" '
                       f'style="font-weight:700;color:#7c3aed;font-size:15px">{html.escape(ticker)}</a>')

        rows.append(f"""
          <tr style="border-bottom:1px solid #f3f4f6">
            <td style="padding:14px 12px;vertical-align:top;min-width:120px">
              {ticker_html}<br>
              <span style="font-size:12px;color:#6b7280">{html.escape(s.get('name',''))}</span>
            </td>
            <td style="padding:14px 12px;vertical-align:top;font-size:14px;font-weight:600;color:#7c3aed">{ipo_date}</td>
            <td style="padding:14px 12px;vertical-align:top;font-size:13px">{price}</td>
            <td style="padding:14px 12px;vertical-align:top;font-size:13px">{proceeds}</td>
            <td style="padding:14px 12px;vertical-align:top">{sig_label}</td>
            <td style="padding:14px 12px;vertical-align:top;font-size:13px;line-height:1.7">
              {breakdown}<br>
              <span style="color:#9ca3af;font-size:12px">{desc}</span>
            </td>
          </tr>""")

    return f"""
      <table style="width:100%;border-collapse:collapse">
        <thead><tr style="font-size:11px;text-transform:uppercase;color:#9ca3af;border-bottom:2px solid #e5e7eb">
          <th style="padding:8px 12px;text-align:left">Ticker</th>
          <th style="padding:8px 12px;text-align:left">IPO Date</th>
          <th style="padding:8px 12px;text-align:left">Expected Price</th>
          <th style="padding:8px 12px;text-align:left">Proceeds</th>
          <th style="padding:8px 12px;text-align:left">Type</th>
          <th style="padding:8px 12px;text-align:left">Holdings</th>
        </tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>"""


def _candidates_html(opps: list[dict]) -> str:
    """
    Auto-discovered candidates: entities mentioned across SEC filings/news that
    aren't already in KNOWN_HOLDING_STOCKS or UPCOMING_IPOS, ranked by how many
    distinct target companies they're linked to.
    """
    known_names = {s["name"].lower() for s in KNOWN_HOLDING_STOCKS} | {s.get("name","").lower() for s in UPCOMING_IPOS}
    forms = {f.lower() for f in DISCOVERY_HEURISTICS["filing_forms"]}
    keywords = [k.lower() for k in DISCOVERY_HEURISTICS["vehicle_keywords"]]

    # entity -> {targets: set, sources: set, latest_link: str, latest_date: str, form_types: set}
    candidates: dict[str, dict] = {}
    for o in opps:
        try:
            extra = json.loads(o.get("extra_json") or "{}")
        except Exception:
            extra = {}
        entity = (extra.get("entity_name") or "").strip()
        form = (extra.get("form_type") or "").lower()
        title = (o.get("title") or "").lower()
        explanation = (o.get("explanation") or "").lower()
        text_blob = f"{entity.lower()} {title} {explanation}"

        if not entity or entity.lower() in known_names:
            continue

        # Must be a filing form we care about, or contain a vehicle keyword
        if form and form not in forms and not any(kw in text_blob for kw in keywords):
            continue
        if not form and not any(kw in text_blob for kw in keywords):
            continue

        rec = candidates.setdefault(entity, {
            "targets": set(), "sources": set(), "forms": set(),
            "latest_link": o.get("link", ""), "latest_date": o.get("discovered_at", ""),
        })
        if o.get("matched_company"):
            rec["targets"].add(o["matched_company"])
        rec["sources"].add(o.get("source", ""))
        if form:
            rec["forms"].add(extra.get("form_type", ""))
        if (o.get("discovered_at") or "") > rec["latest_date"]:
            rec["latest_date"] = o.get("discovered_at", "")
            rec["latest_link"] = o.get("link", "")

    if not candidates:
        return ('<p class="empty">None yet — candidates will appear here after the SEC and news monitors '
                'detect filings from new vehicles that hold target companies.</p>')

    # Rank: more distinct targets first, then most recent
    ranked = sorted(
        candidates.items(),
        key=lambda kv: (len(kv[1]["targets"]), kv[1]["latest_date"]),
        reverse=True,
    )[:25]

    cards = []
    min_pure = DISCOVERY_HEURISTICS.get("min_target_holdings_for_pure_play", 3)
    for entity, rec in ranked:
        targets_html = ", ".join(f'<span style="background:#eff6ff;color:#1e40af;padding:1px 8px;'
                                 f'border-radius:999px;font-size:11px;font-weight:600">{html.escape(t)}</span>'
                                 for t in sorted(rec["targets"]))
        forms_html = ", ".join(html.escape(f) for f in sorted(rec["forms"])) or "—"
        score = len(rec["targets"])
        score_label = ("Pure-play candidate" if score >= min_pure
                       else "Multi-target" if score >= 2 else "Single mention")
        score_color = "#15803d" if score >= min_pure else "#92400e" if score >= 2 else "#6b7280"
        ts = (rec["latest_date"] or "")[:10]

        cards.append(f"""
          <div style="background:#f9fafb;border-left:4px solid #7c3aed;padding:14px 18px;margin-bottom:12px;border-radius:6px">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px">
              <h3 style="margin:0;font-size:15px;color:#111827">{html.escape(entity)}</h3>
              <span style="font-size:11px;color:{score_color};font-weight:700">{score_label} · {score} target{'s' if score != 1 else ''}</span>
            </div>
            <p style="margin:0 0 8px;font-size:12px;color:#6b7280">Forms: {forms_html} &nbsp;·&nbsp; Last seen: {html.escape(ts)}</p>
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px">{targets_html}</div>
            <a href="{html.escape(rec['latest_link'])}" target="_blank"
               style="color:#7c3aed;font-size:13px;font-weight:600;text-decoration:none">View latest filing &#8594;</a>
          </div>""")
    return "".join(cards)


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
    trading     = _trading_table()
    upcoming    = _upcoming_table()
    candidates  = _candidates_html(opps)
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
    .wrap {{ max-width: 1080px; margin: 0 auto; }}
    header {{ background: linear-gradient(135deg,#1e3a5f,#2563eb); color: #fff;
              padding: 32px 28px; border-radius: 14px; margin-bottom: 24px; }}
    header h1 {{ font-size: 26px; margin-bottom: 8px; }}
    header p  {{ opacity: .85; font-size: 14px; line-height: 1.6; }}
    section {{ background: #fff; border-radius: 12px; padding: 24px;
               margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }}
    section h2 {{ font-size: 18px; color: #1e3a5f; padding-bottom: 12px;
                  border-bottom: 2px solid #e5e7eb; margin-bottom: 18px; }}
    .pills {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .empty {{ color: #9ca3af; font-style: italic; padding: 8px 0; font-size: 14px; }}
    code {{ background:#f3f4f6;padding:1px 5px;border-radius:4px;font-size:12px }}
    footer {{ text-align: center; font-size: 12px; color: #9ca3af; margin-top: 32px; }}
    @media(max-width:600px) {{ body {{ padding: 12px; }} header {{ padding: 20px; }} }}
  </style>
</head>
<body>
<div class="wrap">

  <header>
    <h1>&#128202; IPO &amp; Investment Watchlist</h1>
    <p>Tracks publicly traded stocks (and upcoming IPOs) that hold stakes in high-value private unicorns.<br>
       Auto-updated every 30&nbsp;minutes &mdash; last run: <strong>{now}</strong>
       &nbsp;&bull;&nbsp; {total} opportunit{'y' if total==1 else 'ies'} recorded (last 60 days)</p>
  </header>

  <section>
    <h2>&#127919; Tracking</h2>
    <div class="pills">{targets}</div>
  </section>

  <section>
    <h2>&#128200; Trading &mdash; Public Holding Stocks</h2>
    <p style="font-size:13px;color:#6b7280;margin-bottom:16px">
      Live price/NAV/P/E/PEG for stocks that hold our target companies.
      <strong style="color:#15803d">Pure play</strong> = stakes drive most of the stock's value &nbsp;·&nbsp;
      <strong style="color:#92400e">Notable</strong> = meaningful exposure &nbsp;·&nbsp;
      <strong style="color:#1e40af">Indirect</strong> = large company, small relative stake.
      P/E &amp; PEG come from Yahoo Finance and may be blank for funds (use NAV instead).
    </p>
    {trading}
  </section>

  <section>
    <h2>&#128640; Upcoming IPOs &mdash; Same Criteria, Not Yet Trading</h2>
    <p style="font-size:13px;color:#6b7280;margin-bottom:16px">
      Companies/funds with confirmed IPO filings or announced public offerings that hold our target unicorns.
      Add entries to <code>UPCOMING_IPOS</code> in <code>config.py</code> as new filings are confirmed.
    </p>
    {upcoming}
  </section>

  <section>
    <h2>&#128270; Auto-discovered Candidates</h2>
    <p style="font-size:13px;color:#6b7280;margin-bottom:16px">
      New entities surfaced by the SEC and news monitors that look like investment vehicles
      holding our target companies. Ranked by number of distinct target companies referenced.
      Use this as a feeder list for <code>KNOWN_HOLDING_STOCKS</code> / <code>UPCOMING_IPOS</code>.
    </p>
    {candidates}
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
