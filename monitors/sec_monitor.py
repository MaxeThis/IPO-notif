"""
Monitors SEC EDGAR full-text search for S-1 and 13F filings that mention
any of our target private companies.

Uses the free EDGAR EFTS search API — no key required.
Rate limit: be polite, ≤10 requests/second. We run this every 6 hours.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Generator

import requests

import database
from config import TARGET_COMPANIES

log = logging.getLogger(__name__)

EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FILING_BASE = "https://www.sec.gov"

# Form types that signal a company going public or revealing institutional holdings
FILING_FORMS = ["S-1", "S-1/A", "S-11", "F-1", "F-1/A", "13F-HR", "SC 13G", "SC 13D"]

HEADERS = {
    "User-Agent": "IPO-Notif contact@example.com",  # EDGAR requires a real user-agent
    "Accept-Encoding": "gzip, deflate",
}


def _search_edgar(query: str, forms: list[str], days_back: int = 7) -> list[dict]:
    """Run a full-text EDGAR search and return raw hits."""
    start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {
        "q": f'"{query}"',
        "dateRange": "custom",
        "startdt": start_date,
        "forms": ",".join(forms),
        "_source": "file_date,period_of_report,entity_name,file_num,form_type,biz_location,inc_states,category",
        "from": 0,
        "size": 20,
    }
    try:
        resp = requests.get(EDGAR_SEARCH_URL, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data.get("hits", {}).get("hits", [])
    except Exception as exc:
        log.warning("EDGAR search error for '%s': %s", query, exc)
        return []


def _parse_hit(hit: dict, matched_company: str) -> dict | None:
    """Extract the fields we care about from an EDGAR hit."""
    src = hit.get("_source", {})
    accession = hit.get("_id", "")
    if not accession:
        return None

    entity_name = src.get("entity_name", "Unknown")
    form_type = src.get("form_type", "")
    filed_at = src.get("file_date", "")

    # Build a human-readable URL to the filing index
    # Accession numbers look like: 0001234567-25-000001
    acc_clean = accession.replace("-", "")
    cik = src.get("file_num", "").replace("0-", "") or acc_clean[:10]
    filing_url = f"{EDGAR_FILING_BASE}/Archives/edgar/data/{acc_clean[:10]}/{acc_clean}/{accession}-index.htm"

    return {
        "accession_number": accession,
        "entity_name": entity_name,
        "form_type": form_type,
        "filed_at": filed_at,
        "matched_company": matched_company,
        "filing_url": filing_url,
        "source": "SEC EDGAR",
    }


def check_sec_filings() -> Generator[dict, None, None]:
    """
    Yield new (unseen) EDGAR filings that mention any target company.
    Marks each hit as seen before yielding to prevent re-alerting.
    """
    log.info("Checking SEC EDGAR for new filings...")
    for company in TARGET_COMPANIES:
        hits = _search_edgar(company, FILING_FORMS)
        time.sleep(0.5)  # be polite to EDGAR

        for hit in hits:
            parsed = _parse_hit(hit, company)
            if not parsed:
                continue

            accession = parsed["accession_number"]
            if database.is_sec_filing_seen(accession):
                continue

            database.mark_sec_filing_seen(
                accession,
                parsed["entity_name"],
                parsed["form_type"],
                parsed["filed_at"],
            )
            log.info(
                "New SEC filing: %s (%s) mentions %s",
                parsed["entity_name"],
                parsed["form_type"],
                company,
            )
            yield parsed
