"""
Central configuration: target private companies, known public holding stocks,
upcoming IPOs that hold our targets, and discovery heuristics.
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
    "ElevenLabs",
    "Revolut",
    "ByteDance",
    "Canva",
    "Discord",
    "Ramp",
    "Brex",
    "Plaid",
    "xAI",
    "Perplexity",
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
    "ElevenLabs": "~$3.3B",
    "Revolut":    "~$45B",
    "ByteDance":  "~$220B",
    "Canva":      "~$32B",
    "Discord":    "~$15B",
    "Ramp":       "~$13B",
    "Brex":       "~$12B",
    "Plaid":      "~$13B",
    "xAI":        "~$50B",
    "Perplexity": "~$9B",
}

# Publicly traded companies/funds that hold meaningful stakes in the private companies above.
# status:               'trading' = currently public; 'upcoming' = pre-IPO (see UPCOMING_IPOS)
# stake_significance:   'high'   = private stakes dominate the stock's value (pure play)
#                       'medium' = meaningful exposure, stock moves on related news
#                       'low'    = large company, private stake is small relative to market cap
KNOWN_HOLDING_STOCKS = [
    {
        "ticker": "DXYZ",
        "name": "Destiny Tech100 Inc",
        "status": "trading",
        "holdings": ["SpaceX", "OpenAI", "Anthropic", "Discord", "Stripe", "Epic Games"],
        "holdings_pct": {
            "SpaceX":     "~20%",
            "OpenAI":     "~17%",
            "Anthropic":  "~7%",
            "Discord":    "~5%",
            "Stripe":     "~4%",
            "Epic Games": "~3%",
        },
        "description": "Closed-end fund whose NAV is almost entirely private-company stakes. One of the only ways retail investors can buy SpaceX, OpenAI, and Anthropic in a brokerage account.",
        "stake_significance": "high",
    },
    {
        "ticker": "RVI",
        "name": "Robinhood Ventures Fund I",
        "status": "trading",
        "holdings": ["OpenAI", "Stripe", "Databricks", "ElevenLabs", "Revolut", "Ramp"],
        "holdings_pct": {
            "OpenAI":     "~$75M invested (Apr 2026)",
            "Stripe":     "~$14.6M invested",
            "Databricks": "undisclosed stake",
            "ElevenLabs": "undisclosed stake",
            "Revolut":    "undisclosed stake",
            "Ramp":       "undisclosed stake",
        },
        "description": "Robinhood's closed-end fund IPO'd March 6 2026 at $25/share ($658M fund). Dropped 16% on debut. Added a $75M OpenAI stake in April 2026. Pure retail access to pre-IPO unicorns.",
        "stake_significance": "high",
    },
    {
        "ticker": "ARKVX",
        "name": "ARK Venture Fund",
        "status": "trading",
        "holdings": ["SpaceX", "OpenAI", "Anthropic", "Anduril", "Epic Games", "Discord", "Databricks"],
        "holdings_pct": {
            "SpaceX":     "~12%",
            "OpenAI":     "~5%",
            "Anthropic":  "~4%",
            "Anduril":    "~3%",
            "Epic Games": "~3%",
            "Discord":    "~2%",
            "Databricks": "~2%",
        },
        "description": "ARK Invest's interval fund — bought via brokerages with quarterly liquidity. Concentrated in late-stage private tech: SpaceX is the largest holding. Priced at NAV (no premium/discount).",
        "stake_significance": "high",
    },
    {
        "ticker": "SFTBY",
        "name": "SoftBank Group Corp (ADR)",
        "status": "trading",
        "holdings": ["ByteDance", "Stripe", "OpenAI", "Revolut", "Plaid"],
        "holdings_pct": {
            "ByteDance": "~$20B+ via Vision Fund",
            "Stripe":    "Vision Fund stake",
            "OpenAI":    "~$1.5B committed (2024)",
            "Revolut":   "lead investor in Series E",
            "Plaid":     "Vision Fund stake",
        },
        "description": "SoftBank's Vision Fund is one of the world's largest tech investors. Vision Fund holdings dominate SoftBank's NAV — analysts often value SFTBY at a discount to underlying portfolio. Trades at ADR (~half a Japanese share).",
        "stake_significance": "medium",
    },
    {
        "ticker": "TCEHY",
        "name": "Tencent Holdings Ltd (ADR)",
        "status": "trading",
        "holdings": ["Epic Games", "Discord", "ElevenLabs"],
        "holdings_pct": {
            "Epic Games": "~40% stake",
            "Discord":    "minority investor",
            "ElevenLabs": "Series C investor",
        },
        "description": "Owns ~40% of Epic Games (Fortnite, Unreal Engine) — largest single holder. Active investor across global gaming/AI startups. Tencent stake in Epic alone could be worth ~$13B.",
        "stake_significance": "medium",
    },
    {
        "ticker": "CRM",
        "name": "Salesforce Inc",
        "status": "trading",
        "holdings": ["Anthropic", "Stripe", "Databricks"],
        "holdings_pct": {
            "Anthropic":  "Salesforce Ventures lead investor",
            "Stripe":     "Salesforce Ventures stake",
            "Databricks": "strategic partner & investor",
        },
        "description": "Salesforce Ventures has invested heavily in enterprise AI — Anthropic is a flagship portfolio company. Stake is small relative to CRM's $300B+ market cap, but CRM moves on AI/Anthropic news.",
        "stake_significance": "low",
    },
    {
        "ticker": "MSFT",
        "name": "Microsoft Corp",
        "status": "trading",
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
        "status": "trading",
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
        "status": "trading",
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
        "status": "trading",
        "holdings": ["OpenAI", "Anthropic", "Databricks", "xAI", "Perplexity"],
        "holdings_pct": {
            "OpenAI":     "early investor",
            "Anthropic":  "early investor",
            "Databricks": "strategic investor",
            "xAI":        "strategic investor",
            "Perplexity": "Series B investor",
        },
        "description": "Early strategic investor in multiple AI unicorns. As the primary GPU supplier, NVDA stock is a broad proxy for AI growth including all target companies.",
        "stake_significance": "medium",
    },
]

# Upcoming IPOs of companies/funds that hold our target private companies.
# Same screening criteria as KNOWN_HOLDING_STOCKS — these just haven't started trading yet.
# Pulled from S-1 filings, news of IPO filings, fund-launch announcements.
# Update ipo_date when known; "TBD Q3 2026" is fine for indicative dates.
UPCOMING_IPOS = [
    # Add entries with this shape as new IPO filings are confirmed:
    # {
    #     "ticker": "TBD",
    #     "name": "Example Ventures Fund II",
    #     "status": "upcoming",
    #     "ipo_date": "2026-08-15",          # YYYY-MM-DD or "TBD Q3 2026"
    #     "expected_price": "$25/share",
    #     "expected_proceeds": "$500M",
    #     "holdings": ["OpenAI", "Anthropic"],
    #     "holdings_pct": {"OpenAI": "~$50M committed", "Anthropic": "~$30M committed"},
    #     "description": "Filed S-1 on YYYY-MM-DD; closed-end fund modelled on RVI.",
    #     "stake_significance": "high",
    #     "filing_url": "https://www.sec.gov/...",
    # },
]

# Heuristics for auto-discovering candidate stocks/funds from SEC filings & news.
# When the SEC monitor or news monitor sees an entity matching these patterns
# alongside a target-company mention, the dashboard surfaces it as a candidate.
DISCOVERY_HEURISTICS = {
    # SEC filing forms that signal a new investment vehicle holding private companies
    "filing_forms": ["S-1", "S-1/A", "F-1", "F-1/A", "N-2", "N-2/A", "13F-HR", "SC 13G", "SC 13D"],
    # Substrings (case-insensitive) in entity/article text that suggest a private-tech holding vehicle
    "vehicle_keywords": [
        "venture fund", "growth fund", "innovation fund",
        "closed-end fund", "interval fund", "BDC",
        "holding company", "blank check", "SPAC",
        "tech100", "private equity", "secondary fund",
        "pre-IPO fund", "tender offer fund",
    ],
    # Used by ranking heuristic — funds with multiple target-company holdings score higher
    "min_target_holdings_for_pure_play": 3,
}

# Keywords that, combined with a target-company name, signal a NEW holding opportunity
OPPORTUNITY_KEYWORDS = [
    "IPO", "S-1", "going public", "public offering",
    "investment fund", "closed-end fund", "holding company",
    "buys stake", "acquires stake", "invests in",
    "pre-IPO", "secondary shares", "private equity",
    "SPAC", "blank check", "tender offer",
    "interval fund", "venture fund", "BDC",
]

# Alert if a known holding stock moves more than this % in a single session
PRICE_MOVE_THRESHOLD_PCT = 5.0

# Alert if daily volume exceeds this multiple of the 20-day average
VOLUME_SPIKE_MULTIPLIER = 2.5
