"""
IPO & Investment Opportunity Monitor
=====================================
Monitors SEC EDGAR, news, and known holding stocks for early signals
about public investment vehicles that hold Anthropic, OpenAI, SpaceX, etc.

Results are written to docs/index.html and served via GitHub Pages.

Usage:
    python main.py            # run the scheduler (blocks forever)
    python main.py --once     # run one cycle and exit (used by GitHub Actions)
"""
import argparse
import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("main")

import database
import dashboard
from analyzer import explain_sec_filing, explain_news_article, explain_holdings_alert
from monitors.sec_monitor import check_sec_filings
from monitors.news_monitor import check_news
from monitors.holdings_monitor import check_holdings


def run_all_checks() -> None:
    log.info("=== Running checks at %s ===", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

    # 1. SEC filings
    try:
        for alert in check_sec_filings():
            database.save_opportunity(
                source="SEC EDGAR",
                dedup_key=alert["accession_number"],
                matched_company=alert["matched_company"],
                title=f"{alert['form_type']}: {alert['entity_name']}",
                explanation=explain_sec_filing(alert),
                link=alert["filing_url"],
                extra=alert,
            )
    except Exception as exc:
        log.error("SEC monitor error: %s", exc)

    # 2. News
    try:
        for alert in check_news():
            database.save_opportunity(
                source="News",
                dedup_key=alert["url"],
                matched_company=alert["matched_company"],
                title=alert.get("title", ""),
                explanation=explain_news_article(alert),
                link=alert["url"],
                extra=alert,
            )
    except Exception as exc:
        log.error("News monitor error: %s", exc)

    # 3. Holdings price/volume
    try:
        for alert in check_holdings():
            database.save_opportunity(
                source="Holdings Monitor",
                dedup_key=f"{alert['ticker']}-{datetime.utcnow().strftime('%Y-%m-%d')}",
                matched_company=alert["ticker"],
                title=f"{alert['stock_name']} ({alert['ticker']}): {', '.join(alert['triggers'])}",
                explanation=explain_holdings_alert(alert),
                link=f"https://finance.yahoo.com/quote/{alert['ticker']}",
                extra=alert,
            )
    except Exception as exc:
        log.error("Holdings monitor error: %s", exc)

    # Regenerate the dashboard regardless of whether new alerts were found
    log.info("Regenerating dashboard...")
    try:
        dashboard.generate()
        log.info("Dashboard written to docs/index.html")
    except Exception as exc:
        log.error("Dashboard generation error: %s", exc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    database.init_db()

    if args.once:
        run_all_checks()
    else:
        from apscheduler.schedulers.blocking import BlockingScheduler
        scheduler = BlockingScheduler(timezone="UTC")
        scheduler.add_job(run_all_checks, "interval", minutes=30,
                          id="full_check", next_run_time=datetime.utcnow())
        log.info("Scheduler started. Press Ctrl+C to stop.")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            log.info("Scheduler stopped.")
