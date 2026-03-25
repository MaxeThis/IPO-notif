"""
SQLite-backed store for deduplicating alerts and tracking seen filings/articles.
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "state.db")


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS seen_sec_filings (
                accession_number TEXT PRIMARY KEY,
                company_name     TEXT,
                form_type        TEXT,
                filed_at         TEXT,
                created_at       TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS seen_news_articles (
                url        TEXT PRIMARY KEY,
                title      TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS seen_price_alerts (
                ticker     TEXT,
                alert_date TEXT,
                PRIMARY KEY (ticker, alert_date)
            );

            CREATE TABLE IF NOT EXISTS sent_alerts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT,
                key        TEXT UNIQUE,
                subject    TEXT,
                sent_at    TEXT DEFAULT (datetime('now'))
            );
        """)


# ── SEC filings ────────────────────────────────────────────────────────────────

def is_sec_filing_seen(accession_number: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM seen_sec_filings WHERE accession_number = ?",
            (accession_number,),
        ).fetchone()
    return row is not None


def mark_sec_filing_seen(accession_number: str, company_name: str, form_type: str, filed_at: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO seen_sec_filings (accession_number, company_name, form_type, filed_at) VALUES (?,?,?,?)",
            (accession_number, company_name, form_type, filed_at),
        )


# ── News articles ──────────────────────────────────────────────────────────────

def is_article_seen(url: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM seen_news_articles WHERE url = ?", (url,)
        ).fetchone()
    return row is not None


def mark_article_seen(url: str, title: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO seen_news_articles (url, title) VALUES (?,?)",
            (url, title),
        )


# ── Price alerts ───────────────────────────────────────────────────────────────

def is_price_alert_sent_today(ticker: str) -> bool:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM seen_price_alerts WHERE ticker = ? AND alert_date = ?",
            (ticker, today),
        ).fetchone()
    return row is not None


def mark_price_alert_sent(ticker: str) -> None:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO seen_price_alerts (ticker, alert_date) VALUES (?,?)",
            (ticker, today),
        )


# ── Sent alerts (general dedup) ────────────────────────────────────────────────

def is_alert_sent(key: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM sent_alerts WHERE key = ?", (key,)
        ).fetchone()
    return row is not None


def mark_alert_sent(alert_type: str, key: str, subject: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO sent_alerts (alert_type, key, subject) VALUES (?,?,?)",
            (alert_type, key, subject),
        )
