"""
Monitors Google News RSS and optionally NewsAPI for articles that mention
a target private company alongside opportunity-signal keywords.

Google News RSS is completely free with no API key.
"""
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Generator
from urllib.parse import quote_plus

import requests

import database
from config import TARGET_COMPANIES, OPPORTUNITY_KEYWORDS

log = logging.getLogger(__name__)

GNEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
NEWSAPI_URL = "https://newsapi.org/v2/everything"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; IPO-Notif-Bot/1.0)"}


def _fetch_google_news(query: str) -> list[dict]:
    """Fetch articles from Google News RSS for a search query."""
    url = GNEWS_RSS.format(query=quote_plus(query))
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date_str = (item.findtext("pubDate") or "").strip()
            description = (item.findtext("description") or "").strip()

            if not link or not title:
                continue

            # Only look at articles from the last 48 hours
            if pub_date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    pub_dt = parsedate_to_datetime(pub_date_str).replace(tzinfo=None)
                    if pub_dt < datetime.utcnow() - timedelta(hours=48):
                        continue
                except Exception:
                    pass

            articles.append({
                "title": title,
                "url": link,
                "description": description,
                "published_at": pub_date_str,
            })
        return articles
    except Exception as exc:
        log.warning("Google News RSS error for '%s': %s", query, exc)
        return []


def _fetch_newsapi(company: str, api_key: str) -> list[dict]:
    """Fetch articles from NewsAPI (optional, requires key)."""
    try:
        resp = requests.get(
            NEWSAPI_URL,
            params={
                "q": company,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "from": (datetime.utcnow() - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S"),
                "apiKey": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "description": a.get("description", ""),
                "published_at": a.get("publishedAt", ""),
            }
            for a in data.get("articles", [])
            if a.get("url") and a.get("title")
        ]
    except Exception as exc:
        log.warning("NewsAPI error for '%s': %s", company, exc)
        return []


def _is_opportunity_article(title: str, description: str, target_company: str) -> bool:
    """Return True if the article seems to signal an investment opportunity."""
    text = (title + " " + description).lower()
    if target_company.lower() not in text:
        return False
    return any(kw.lower() in text for kw in OPPORTUNITY_KEYWORDS)


def check_news() -> Generator[dict, None, None]:
    """
    Yield new (unseen) news articles that match a target company + opportunity keyword.
    """
    log.info("Checking news for investment opportunities...")
    news_api_key = os.getenv("NEWS_API_KEY", "")

    for company in TARGET_COMPANIES:
        # Build a focused query: company name + at least one investment keyword
        query = f"{company} IPO OR investment fund OR holding company OR stake OR public offering"
        articles = _fetch_google_news(query)

        if news_api_key:
            articles += _fetch_newsapi(company, news_api_key)

        for article in articles:
            url = article["url"]
            title = article["title"]

            if database.is_article_seen(url):
                continue

            if not _is_opportunity_article(title, article.get("description", ""), company):
                database.mark_article_seen(url, title)  # mark seen so we skip next time
                continue

            database.mark_article_seen(url, title)
            article["matched_company"] = company
            article["source"] = "News"
            log.info("New opportunity article: %s (matched: %s)", title[:80], company)
            yield article
