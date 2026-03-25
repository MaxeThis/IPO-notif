"""
Central configuration: target private companies and known public holding stocks.
"""

# Private unicorns we care about — add/remove as you like
TARGET_COMPANIES = [
    "Anthropic",
    "OpenAI",
    "SpaceX",
    "Stripe",
    "Databricks",
    "Epic Games",
]

# Estimated valuations (USD billions) for context in alerts — keep roughly updated
COMPANY_VALUATIONS = {
    "Anthropic":  "~$61B",
    "OpenAI":     "~$157B",
    "SpaceX":     "~$350B",
    "Stripe":     "~$65B",
    "Databricks": "~$62B",
    "Epic Games": "~$32B",
}

# Already-known public companies / funds that hold these private stakes.
# The monitor tracks price + volume and alerts on significant moves.
KNOWN_HOLDING_STOCKS = [
    {
        "ticker": "DXYZ",
        "name": "Destiny Tech100 Inc",
        "holdings": ["OpenAI", "SpaceX", "Anthropic", "Discord", "Stripe"],
        "description": "Closed-end fund that owns direct stakes in top pre-IPO tech companies.",
    },
]

# Keywords that, combined with a target-company name, signal a NEW holding opportunity
OPPORTUNITY_KEYWORDS = [
    "IPO", "S-1", "going public", "public offering",
    "investment fund", "closed-end fund", "holding company",
    "buys stake", "acquires stake", "invests in",
    "pre-IPO", "secondary shares", "private equity",
    "SPAC", "blank check",
]

# Alert if a known holding stock moves more than this % in a single session
PRICE_MOVE_THRESHOLD_PCT = 5.0

# Alert if daily volume exceeds this multiple of the 20-day average
VOLUME_SPIKE_MULTIPLIER = 2.5
