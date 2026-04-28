"""
Tracks known publicly-traded holding stocks (e.g. DXYZ) for:
  - Significant price moves (>PRICE_MOVE_THRESHOLD_PCT in a session)
  - Volume spikes (>VOLUME_SPIKE_MULTIPLIER × 20-day avg)

Uses Yahoo Finance's free v8 chart API directly (no API key required).
"""
import logging
from datetime import datetime
from typing import Generator

import requests

import database
from config import KNOWN_HOLDING_STOCKS, PRICE_MOVE_THRESHOLD_PCT, VOLUME_SPIKE_MULTIPLIER

log = logging.getLogger(__name__)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IPO-Notif/1.0)",
    "Accept": "application/json",
}


def _get_stock_data(ticker: str) -> dict | None:
    """Fetch ~22 days of daily OHLCV from Yahoo Finance chart API."""
    try:
        resp = requests.get(
            YAHOO_CHART_URL.format(ticker=ticker),
            params={"interval": "1d", "range": "1mo"},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        result = data.get("chart", {}).get("result", [])
        if not result:
            log.warning("No chart data for %s", ticker)
            return None

        chart = result[0]
        quotes = chart.get("indicators", {}).get("quote", [{}])[0]
        timestamps = chart.get("timestamp", [])

        closes = [c for c in quotes.get("close", []) if c is not None]
        volumes = [v for v in quotes.get("volume", []) if v is not None]

        if len(closes) < 2 or len(volumes) < 2:
            return None

        current_price = closes[-1]
        prev_close = closes[-2]
        pct_change = ((current_price - prev_close) / prev_close) * 100

        avg_volume = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 0
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        # Get market cap from quote endpoint
        market_cap = None
        long_name = ticker
        try:
            q_resp = requests.get(
                YAHOO_QUOTE_URL,
                params={"symbols": ticker, "fields": "marketCap,longName"},
                headers=HEADERS,
                timeout=10,
            )
            if q_resp.ok:
                q_data = q_resp.json()
                q_result = q_data.get("quoteResponse", {}).get("result", [])
                if q_result:
                    market_cap = q_result[0].get("marketCap")
                    long_name = q_result[0].get("longName", ticker)
        except Exception:
            pass

        return {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "prev_close": round(prev_close, 2),
            "pct_change": round(pct_change, 2),
            "volume": int(current_volume),
            "avg_volume": int(avg_volume),
            "volume_ratio": round(volume_ratio, 2),
            "market_cap": market_cap,
            "long_name": long_name,
        }

    except Exception as exc:
        log.warning("Yahoo Finance error for %s: %s", ticker, exc)
        return None


def check_holdings() -> Generator[dict, None, None]:
    """
    Yield alert dicts for known holding stocks that have moved significantly today.
    """
    log.info("Checking known holding stocks...")

    for stock_cfg in KNOWN_HOLDING_STOCKS:
        # Skip pre-IPO entries — they don't have a tradeable price feed yet
        if stock_cfg.get("status", "trading") != "trading":
            continue

        ticker = stock_cfg["ticker"]

        # Only alert once per ticker per calendar day
        if database.is_price_alert_sent_today(ticker):
            continue

        data = _get_stock_data(ticker)
        if not data:
            continue

        price_triggered = abs(data["pct_change"]) >= PRICE_MOVE_THRESHOLD_PCT
        volume_triggered = data["volume_ratio"] >= VOLUME_SPIKE_MULTIPLIER

        if not (price_triggered or volume_triggered):
            continue

        triggers = []
        if price_triggered:
            direction = "up" if data["pct_change"] > 0 else "down"
            triggers.append(f"{abs(data['pct_change'])}% {direction} today")
        if volume_triggered:
            triggers.append(f"{data['volume_ratio']}× average volume")

        database.mark_price_alert_sent(ticker)
        log.info("Holdings alert: %s — %s", ticker, ", ".join(triggers))

        yield {
            "source": "Holdings Monitor",
            "ticker": ticker,
            "stock_name": stock_cfg["name"],
            "holdings": stock_cfg["holdings"],
            "description": stock_cfg["description"],
            "triggers": triggers,
            **data,
        }
