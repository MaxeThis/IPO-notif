"""
Generates a plain-English explanation of why each alert is an investment opportunity.
No external AI calls — uses template logic based on available data.
"""
from config import COMPANY_VALUATIONS


def explain_sec_filing(alert: dict) -> str:
    company = alert["matched_company"]
    entity = alert["entity_name"]
    form = alert["form_type"]
    valuation = COMPANY_VALUATIONS.get(company, "multi-billion dollar")

    if form in ("S-1", "S-1/A", "F-1", "F-1/A"):
        return (
            f"<strong>{entity}</strong> filed an <strong>{form}</strong> (IPO registration) "
            f"with the SEC, and the filing mentions <strong>{company}</strong>. "
            f"This is significant because {company} — currently valued at "
            f"<strong>{valuation}</strong> — is a private company not directly accessible "
            f"to retail investors. If {entity} holds a stake in {company}, buying shares "
            f"of {entity} may be one of the few ways to get indirect exposure to "
            f"{company}'s growth before or instead of a direct IPO. "
            f"Review the filing to confirm the size and nature of the {company} position."
        )

    if form in ("13F-HR",):
        return (
            f"An institutional investor (<strong>{entity}</strong>) disclosed holdings "
            f"that include <strong>{company}</strong> in a <strong>13F</strong> filing. "
            f"13F filings reveal what large funds own at the end of each quarter. "
            f"If this fund is publicly traded or has a publicly traded vehicle, "
            f"it could represent a way to gain exposure to {company} "
            f"(currently valued at {valuation})."
        )

    if form in ("SC 13G", "SC 13D"):
        return (
            f"<strong>{entity}</strong> filed a <strong>{form}</strong>, indicating it has "
            f"accumulated a significant (≥5%) stake in a company linked to "
            f"<strong>{company}</strong>. This can signal activist interest or a "
            f"strategic position related to {company}'s ecosystem."
        )

    return (
        f"<strong>{entity}</strong> filed a <strong>{form}</strong> that references "
        f"<strong>{company}</strong> (valued at {valuation}). "
        f"This filing may indicate a new investment vehicle or corporate structure "
        f"that provides exposure to {company}. Review the filing for details."
    )


def explain_news_article(alert: dict) -> str:
    company = alert["matched_company"]
    valuation = COMPANY_VALUATIONS.get(company, "multi-billion dollar")
    title = alert.get("title", "")
    description = alert.get("description", "")

    snippet = description[:300] if description else title

    return (
        f"A news article was detected mentioning <strong>{company}</strong> "
        f"(currently valued at <strong>{valuation}</strong>) alongside investment "
        f"opportunity keywords (IPO, fund, stake, etc.).<br><br>"
        f"<em>{snippet}</em><br><br>"
        f"This may indicate a new public vehicle giving retail investors access to "
        f"{company} equity — which is otherwise unavailable on public markets."
    )


def explain_holdings_alert(alert: dict) -> str:
    ticker = alert["ticker"]
    name = alert["stock_name"]
    holdings_str = ", ".join(alert["holdings"])
    triggers_str = " and ".join(alert["triggers"])
    description = alert.get("description", "")

    market_cap_str = ""
    mc = alert.get("market_cap")
    if mc:
        market_cap_str = f"Market cap: <strong>${mc:,.0f}</strong>. "

    return (
        f"<strong>{name} ({ticker})</strong> moved <strong>{triggers_str}</strong>.<br><br>"
        f"{description}<br><br>"
        f"<strong>Reported private-company holdings:</strong> {holdings_str}.<br>"
        f"{market_cap_str}"
        f"Unusual price or volume activity in holding companies often precedes "
        f"broader market awareness of their private-company stakes. "
        f"Early positioning before mainstream coverage can offer significant upside."
    )


def build_email_content(alerts: list[dict]) -> tuple[str, str]:
    """
    Returns (subject, html_body) for an email summarising all alerts.
    """
    if not alerts:
        return "", ""

    # Subject line
    companies = list({a.get("matched_company") or a.get("ticker", "") for a in alerts})
    company_str = ", ".join(companies[:3])
    if len(companies) > 3:
        company_str += f" +{len(companies) - 3} more"
    subject = f"[IPO Alert] {len(alerts)} new opportunit{'y' if len(alerts)==1 else 'ies'} — {company_str}"

    # HTML body
    sections = []
    for alert in alerts:
        source = alert.get("source", "")

        if source == "SEC EDGAR":
            heading = f"📄 SEC Filing — {alert['form_type']}: {alert['entity_name']}"
            explanation = explain_sec_filing(alert)
            link_html = f'<a href="{alert["filing_url"]}">View Filing on SEC EDGAR →</a>'
            meta = f"Filed: {alert.get('filed_at', 'N/A')} | Matched: {alert['matched_company']}"

        elif source == "News":
            heading = f"📰 News Alert — {alert['matched_company']}"
            explanation = explain_news_article(alert)
            link_html = f'<a href="{alert["url"]}">Read Article →</a>'
            meta = f"Published: {alert.get('published_at', 'N/A')}"

        elif source == "Holdings Monitor":
            ticker = alert["ticker"]
            pct = alert["pct_change"]
            color = "#16a34a" if pct >= 0 else "#dc2626"
            heading = f"📈 Holdings Alert — {ticker} ({'+' if pct>=0 else ''}{pct}%)"
            explanation = explain_holdings_alert(alert)
            link_html = (
                f'<a href="https://finance.yahoo.com/quote/{ticker}">View {ticker} on Yahoo Finance →</a>'
            )
            meta = (
                f"Price: ${alert['current_price']} | "
                f"Volume: {alert['volume']:,} ({alert['volume_ratio']}× avg) | "
                f"Change: <span style=\"color:{color}\">{'+' if pct>=0 else ''}{pct}%</span>"
            )
        else:
            continue

        sections.append(f"""
        <div style="background:#f9fafb;border-left:4px solid #2563eb;padding:16px 20px;margin-bottom:24px;border-radius:4px;">
          <h2 style="margin:0 0 8px 0;font-size:16px;color:#1e3a5f;">{heading}</h2>
          <p style="margin:0 0 8px 0;font-size:13px;color:#6b7280;">{meta}</p>
          <p style="margin:0 0 12px 0;font-size:14px;line-height:1.6;color:#374151;">{explanation}</p>
          <p style="margin:0;">{link_html}</p>
        </div>
        """)

    now = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#111827;">
      <div style="background:#1e3a5f;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0;margin-bottom:0;">
        <h1 style="margin:0;font-size:20px;">IPO & Investment Opportunity Alert</h1>
        <p style="margin:6px 0 0 0;font-size:13px;opacity:0.8;">{now} — {len(alerts)} alert{'s' if len(alerts)!=1 else ''}</p>
      </div>
      <div style="background:#fff;border:1px solid #e5e7eb;border-top:none;padding:24px;border-radius:0 0 8px 8px;">
        {"".join(sections)}
        <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
        <p style="font-size:12px;color:#9ca3af;">
          This is an automated alert from your IPO-Notif monitor.<br>
          Targets: Anthropic · OpenAI · SpaceX · Stripe · Databricks · Epic Games<br>
          <strong>Not financial advice.</strong> Always do your own research before investing.
        </p>
      </div>
    </body>
    </html>
    """

    return subject, html
