"""
IPO & Investment Opportunity Notifier
======================================
Monitors SEC EDGAR, news, and known holding stocks for early signals
about public investment vehicles that hold Anthropic, OpenAI, SpaceX, etc.

Usage:
    python main.py            # run the scheduler (blocks forever)
    python main.py --once     # run all checks once and exit (good for cron/testing)
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
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ipo_notif.log"),
    ],
)
log = logging.getLogger("main")

import database
import notifier
from analyzer import build_email_content
from monitors.sec_monitor import check_sec_filings
from monitors.news_monitor import check_news
from monitors.holdings_monitor import check_holdings


def _validate_env() -> None:
    required = ["EMAIL_SENDER", "EMAIL_PASSWORD", "EMAIL_RECIPIENT"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        log.error("Missing required environment variables: %s", ", ".join(missing))
        log.error("Copy .env.example → .env and fill in your email credentials.")
        sys.exit(1)


def run_all_checks() -> None:
    """Collect alerts from all monitors and send a single batched email."""
    log.info("=== Running all checks at %s ===", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    alerts = []

    # 1. SEC filings
    try:
        for alert in check_sec_filings():
            alerts.append(alert)
    except Exception as exc:
        log.error("SEC monitor error: %s", exc)

    # 2. News
    try:
        for alert in check_news():
            alerts.append(alert)
    except Exception as exc:
        log.error("News monitor error: %s", exc)

    # 3. Known holdings price/volume
    try:
        for alert in check_holdings():
            alerts.append(alert)
    except Exception as exc:
        log.error("Holdings monitor error: %s", exc)

    if not alerts:
        log.info("No new alerts this cycle.")
        return

    log.info("Found %d new alert(s) — sending email.", len(alerts))
    subject, html = build_email_content(alerts)
    if subject and html:
        notifier.send_email(subject, html)


def run_scheduler() -> None:
    """Run checks on a schedule using APScheduler."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    sec_interval = int(os.getenv("SEC_CHECK_INTERVAL", "360"))   # default 6 hours
    news_interval = int(os.getenv("NEWS_CHECK_INTERVAL", "60"))  # default 1 hour
    hold_interval = int(os.getenv("HOLDINGS_CHECK_INTERVAL", "30"))  # default 30 min

    scheduler = BlockingScheduler(timezone="UTC")

    # Run once at startup, then on schedule
    scheduler.add_job(run_all_checks, "interval", minutes=min(sec_interval, news_interval, hold_interval),
                      id="full_check", next_run_time=datetime.utcnow())

    log.info(
        "Scheduler started. Checks run every %d minutes. Press Ctrl+C to stop.",
        min(sec_interval, news_interval, hold_interval),
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IPO & Investment Opportunity Notifier")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run all checks once and exit (useful for cron jobs)",
    )
    args = parser.parse_args()

    _validate_env()
    database.init_db()

    if args.once:
        run_all_checks()
    else:
        run_scheduler()
