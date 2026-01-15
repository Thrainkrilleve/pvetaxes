from app_utils.django import clean_setting

PVETAXES_CORP_WALLET_DIVISION = clean_setting("PVETAXES_CORP_WALLET_DIVISION", 1)

PVETAXES_UPDATE_LEDGER_STALE = clean_setting("PVETAXES_UPDATE_LEDGER_STALE", 240)
"""Minutes after which a character's wallet journal is considered stale"""

PVETAXES_UPDATE_STALE_OFFSET = clean_setting("PVETAXES_UPDATE_STALE_OFFSET", 5)
"""Actual value for considering staleness minus this offset"""

PVETAXES_TASKS_OBJECT_CACHE_TIMEOUT = clean_setting(
    "PVETAXES_TASKS_OBJECT_CACHE_TIMEOUT", 600
)

PVETAXES_TASKS_TIME_LIMIT = clean_setting("PVETAXES_TASKS_TIME_LIMIT", 7200)
"""Global timeout for tasks in seconds"""

PVETAXES_ALLOW_ANALYTICS = clean_setting("PVETAXES_ALLOW_ANALYTICS", True)

PVETAXES_UNKNOWN_TAX_RATE = clean_setting("PVETAXES_UNKNOWN_TAX_RATE", 0.10)

# Tax rates for different activities
PVETAXES_TAX_BOUNTIES = clean_setting("PVETAXES_TAX_BOUNTIES", 0.10)
"""Tax rate for bounty payouts (ratting)"""

PVETAXES_TAX_ESS = clean_setting("PVETAXES_TAX_ESS", 0.10)
"""Tax rate for ESS payouts"""

PVETAXES_TAX_MISSIONS = clean_setting("PVETAXES_TAX_MISSIONS", 0.10)
"""Tax rate for mission rewards"""

PVETAXES_TAX_INCURSIONS = clean_setting("PVETAXES_TAX_INCURSIONS", 0.10)
"""Tax rate for incursion payouts"""

# Security status tax rates
PVETAXES_TAX_HISEC = clean_setting("PVETAXES_TAX_HISEC", 0.05)
PVETAXES_TAX_LOSEC = clean_setting("PVETAXES_TAX_LOSEC", 0.08)
PVETAXES_TAX_NULLSEC = clean_setting("PVETAXES_TAX_NULLSEC", 0.10)
PVETAXES_TAX_JSPACE = clean_setting("PVETAXES_TAX_JSPACE", 0.12)
PVETAXES_TAX_POCHVEN = clean_setting("PVETAXES_TAX_POCHVEN", 0.15)

# System whitelist and blacklist
PVETAXES_WHITELIST = clean_setting("PVETAXES_WHITELIST", [])
"""List of solar system IDs to tax. If empty, all systems are taxed (subject to blacklist)"""

PVETAXES_BLACKLIST = clean_setting("PVETAXES_BLACKLIST", [])
"""List of solar system IDs to exclude from taxation"""

# Tax by security status toggles
PVETAXES_TAX_HISEC_ENABLED = clean_setting("PVETAXES_TAX_HISEC_ENABLED", True)
PVETAXES_TAX_LOSEC_ENABLED = clean_setting("PVETAXES_TAX_LOSEC_ENABLED", True)
PVETAXES_TAX_NULLSEC_ENABLED = clean_setting("PVETAXES_TAX_NULLSEC_ENABLED", True)
PVETAXES_TAX_JSPACE_ENABLED = clean_setting("PVETAXES_TAX_JSPACE_ENABLED", True)
PVETAXES_TAX_POCHVEN_ENABLED = clean_setting("PVETAXES_TAX_POCHVEN_ENABLED", True)

# Leaderboard settings
PVETAXES_LEADERBOARD_TAXABLE_ONLY = clean_setting("PVETAXES_LEADERBOARD_TAXABLE_ONLY", True)

# Interest rate
PVETAXES_INTEREST_RATE = clean_setting("PVETAXES_INTEREST_RATE", 0.0)
"""Monthly interest rate applied to outstanding tax balances"""

# Notification settings
PVETAXES_PING_THRESHOLD = clean_setting("PVETAXES_PING_THRESHOLD", 10000000)
"""Minimum tax balance (ISK) before notifications are sent"""

PVETAXES_PING_CURRENT_THRESHOLD = clean_setting("PVETAXES_PING_CURRENT_THRESHOLD", 1000000)

PVETAXES_PING_FIRST_MSG = clean_setting(
    "PVETAXES_PING_FIRST_MSG",
    "You owe {:.2f} million ISK in PVE taxes. Please pay soon."
)

PVETAXES_PING_SECOND_MSG = clean_setting(
    "PVETAXES_PING_SECOND_MSG",
    "Reminder: You still owe {:.2f} million ISK in PVE taxes."
)

PVETAXES_PING_CURRENT_MSG = clean_setting(
    "PVETAXES_PING_CURRENT_MSG",
    "This month you owe {:.2f} million ISK in PVE taxes."
)

PVETAXES_PING_INTEREST_APPLIED = clean_setting(
    "PVETAXES_PING_INTEREST_APPLIED",
    "Interest of {:.2f} million ISK has been applied to your tax balance."
)

# Discord settings
PVETAXES_DISCORD_WEBHOOK_URL = clean_setting("PVETAXES_DISCORD_WEBHOOK_URL", "")
PVETAXES_DISCORD_BOT_TOKEN = clean_setting("PVETAXES_DISCORD_BOT_TOKEN", "")
PVETAXES_DISCORD_SEND_INDIVIDUAL_DMS = clean_setting("PVETAXES_DISCORD_SEND_INDIVIDUAL_DMS", False)
PVETAXES_DISCORD_SEND_CORP_SUMMARY = clean_setting("PVETAXES_DISCORD_SEND_CORP_SUMMARY", False)
