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
    "Anduril",
]

# Estimated valuations (USD billions) for context in alerts — keep roughly updated
COMPANY_VALUATIONS = {
    "Anthropic":  "~$61B",
    "OpenAI":     "~$157B",
    "SpaceX":     "~$350B",
    "Stripe":     "~$65B",
    "Databricks": "~$62B",
    "Epic Games": "~$32B",
    "Anduril":    "~$28B",
}

# Publicly traded companies/funds that hold meaningful stakes in the private companies above.
# holdings_pct: approximate % of the fund/portfolio each private holding represents.
# stake_significance: 'high' = private stakes dominate the stock's value;
#                     'medium' = notable but not the whole story;
#                     'low' = large company, small relative stake.
KNOWN_HOLDING_STOCKS = [
    {
        "ticker": "DXYZ",
        "name": "Destiny Tech100 Inc",
        "holdings": ["SpaceX", "OpenAI", "Anthropic", "Discord", "Stripe"],
        "holdings_pct": {
            "SpaceX":    "~20%",
            "OpenAI":    "~17%",
            "Anthropic": "~7%",
            "Discord":   "~5%",
            "Stripe":    "~4%",
        },
        "description": "Closed-end fund whose NAV is almost entirely private-company stakes. One of the only ways retail investors can buy SpaceX, OpenAI, and Anthropic in a brokerage account.",
        "stake_significance": "high",
    },
    {
        "ticker": "MSFT",
        "name": "Microsoft Corp",
        "holdings": ["OpenAI"],
        "holdings_pct": {
            "OpenAI": "~$13B invested",
        },
        "description": "Invested ~$13B in OpenAI and provides Azure as its exclusive cloud. OpenAI is a small % of Microsoft's $3T market cap, but MSFT moves on OpenAI news.",
        "stake_significance": "low",
    },
    {
        "ticker": "GOOGL",
        "name": "Alphabet Inc",
        "holdings": ["Anthropic"],
        "holdings_pct": {
            "Anthropic": "~$2B invested",
        },
        "description": "Invested ~$2B in Anthropic via Google Cloud partnership. Small relative to Alphabet's market cap, but stock reacts to Anthropic milestones.",
        "stake_significance": "low",
    },
    {
        "ticker": "AMZN",
        "name": "Amazon.com Inc",
        "holdings": ["Anthropic"],
        "holdings_pct": {
            "Anthropic": "~$4B invested",
        },
        "description": "Committed up to $4B in Anthropic through AWS. Anthropic models power many AWS AI products.",
        "stake_significance": "low",
    },
    {
        "ticker": "NVDA",
        "name": "NVIDIA Corp",
        "holdings": ["OpenAI", "Anthropic", "Databricks"],
        "holdings_pct": {
            "OpenAI":     "early investor",
            "Anthropic":  "early investor",
            "Databricks": "strategic investor",
        },
        "description": "Early strategic investor in multiple AI unicorns. As the primary GPU supplier, NVDA stock is a broad proxy for AI growth including all target companies.",
        "stake_significance": "medium",
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
