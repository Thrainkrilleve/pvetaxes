# PVE Taxes

An Alliance Auth app for tracking PVE activities (ratting/bounties, ESS, missions, and incursions) and charging taxes to corporation members.

## Features

- **Activity Tracking**: Automatically tracks bounty payouts, ESS payouts, mission rewards, and incursion payouts
- **Tax Calculation**: Configurable tax rates by activity type and security status (hisec, lowsec, nullsec, J-space, Pochven)
- **Monthly Leaderboards**: Shows top earners by activity type
- **Multiple Corps**: Supports multiple corporations under one system (add one character with the accountant role per corp)
- **Tax Credit System**: Offset, zero, or award tax credits to any user
- **Monthly Interest**: Optional interest rate that penalizes unpaid tax balances
- **Discord Integration**: 
  - Channel webhooks for public notifications
  - Individual DMs via Discord bot
  - Corp summaries showing all outstanding taxes
- **User Dashboard**: Users can view their PVE activity, taxes owed, and payment history
- **Auditor Access**: Special permission for viewing all character data
- **Whitelist/Blacklist**: Control which systems are taxable
- **Flexible Tax Rates**: Set different rates for different security statuses and activity types

## Tracked Activities

### Ratting/Bounties
- Tracks bounty payouts from NPC kills
- ESI ref_type: `bounty_prizes`

### ESS Payouts
- Tracks payments from Encounter Surveillance Systems
- ESI ref_type: `ess_escrow_transfer`

### Missions
- Tracks mission rewards and time bonuses
- ESI ref_types: `agent_mission_reward`, `agent_mission_time_bonus_reward`

### Incursions
- Tracks incursion payouts
- ESI ref_type: `corporate_reward_payout`

## Installation

### Requirements

- Alliance Auth >= 2.15.0
- Python >= 3.8
- Django >= 3.2

### Steps

1. Install the package:
```bash
pip install aa-pvetaxes
```

2. Add `pvetaxes` to your `INSTALLED_APPS` in `settings/local.py`:
```python
INSTALLED_APPS = [
    # ... other apps
    'pvetaxes',
]
```

3. Add the app's URLs to your main `urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    # ... other patterns
    path('pvetaxes/', include('pvetaxes.urls')),
]
```

4. Run migrations:
```bash
python manage.py migrate pvetaxes
```

5. Restart your supervisor services

6. Grant permissions to appropriate groups in the Django admin panel:
   - `pvetaxes.basic_access` - Basic user access
   - `pvetaxes.admin_access` - Admin access for managing characters and settings
   - `pvetaxes.auditor_access` - View all character data

## Configuration

Add these settings to your `settings/local.py` to customize behavior:

### Tax Rates

```python
# Activity-specific tax rates
PVETAXES_TAX_BOUNTIES = 0.10  # 10% tax on bounties
PVETAXES_TAX_ESS = 0.10
PVETAXES_TAX_MISSIONS = 0.10
PVETAXES_TAX_INCURSIONS = 0.10

# Security status-based tax rates (these override activity-specific if set)
PVETAXES_TAX_HISEC = 0.05  # 5% in high-sec
PVETAXES_TAX_LOSEC = 0.08  # 8% in low-sec
PVETAXES_TAX_NULLSEC = 0.10  # 10% in null-sec
PVETAXES_TAX_JSPACE = 0.12  # 12% in wormhole space
PVETAXES_TAX_POCHVEN = 0.15  # 15% in Pochven

# Enable/disable taxation by security status
PVETAXES_TAX_HISEC_ENABLED = True
PVETAXES_TAX_LOSEC_ENABLED = True
PVETAXES_TAX_NULLSEC_ENABLED = True
PVETAXES_TAX_JSPACE_ENABLED = True
PVETAXES_TAX_POCHVEN_ENABLED = True
```

### System Filtering

```python
# Only tax these systems (empty list = tax all systems except blacklist)
PVETAXES_WHITELIST = []

# Never tax these systems
PVETAXES_BLACKLIST = [30000142]  # Example: Jita
```

### Interest and Notifications

```python
# Monthly interest rate on outstanding balances
PVETAXES_INTEREST_RATE = 0.02  # 2% per month

# Minimum balance before sending notifications
PVETAXES_PING_THRESHOLD = 10000000  # 10M ISK

# Notification messages
PVETAXES_PING_FIRST_MSG = "You owe {:.2f} million ISK in PVE taxes. Please pay soon."
PVETAXES_PING_INTEREST_APPLIED = "Interest of {:.2f} million ISK has been applied to your tax balance."
```

### Discord Integration

```python
# Discord webhook for channel notifications
PVETAXES_DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."

# Discord bot token for DMs
PVETAXES_DISCORD_BOT_TOKEN = "your_bot_token_here"

# Enable individual DMs
PVETAXES_DISCORD_SEND_INDIVIDUAL_DMS = False

# Enable corp-wide summary
PVETAXES_DISCORD_SEND_CORP_SUMMARY = False
```

### Other Settings

```python
# Corp wallet division to monitor for payments
PVETAXES_CORP_WALLET_DIVISION = 1

# How often to update (minutes)
PVETAXES_UPDATE_LEDGER_STALE = 240  # 4 hours

# Celery task timeout
PVETAXES_TASKS_TIME_LIMIT = 7200  # 2 hours
```

## Usage

### For Administrators

1. **Add Admin Characters**: In the Django admin panel, add characters with the "Accountant" role from each corporation you want to track
2. **Configure Settings**: Set up tax rates, interest rates, and Discord integration in the Settings model
3. **Grant Permissions**: Assign appropriate permissions to your groups

### For Users

1. **Add Characters**: Users add their characters through the launcher page
2. **View Activity**: See your PVE earnings and taxes in the user dashboard
3. **Make Payments**: Send ISK to the corp wallet with the configured phrase in the description

## Management Commands

```bash
# Update all characters' wallet journals
python manage.py pvetaxes_update_all

# Update a specific character
python manage.py pvetaxes_update_character <character_id>

# Update statistics
python manage.py pvetaxes_update_stats

# Run monthly maintenance (interest, notifications)
python manage.py pvetaxes_monthly_tasks

# Zero all balances (WARNING: Irreversible!)
python manage.py pvetaxes_zero_balances --confirm
```

## Periodic Tasks

Set up these Celery beat tasks in your `settings/local.py`:

```python
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # Update all characters every 4 hours
    'pvetaxes_update_all': {
        'task': 'pvetaxes.tasks.update_all_characters',
        'schedule': crontab(minute=0, hour='*/4'),
    },
    # Update admin wallets every hour
    'pvetaxes_update_admins': {
        'task': 'pvetaxes.tasks.update_all_admins',
        'schedule': crontab(minute=30),
    },
    # Update stats daily
    'pvetaxes_update_stats': {
        'task': 'pvetaxes.tasks.update_stats',
        'schedule': crontab(minute=0, hour=6),
    },
    # Monthly maintenance on the 1st of each month
    'pvetaxes_monthly': {
        'task': 'pvetaxes.tasks.run_monthly_tasks',
        'schedule': crontab(minute=0, hour=12, day_of_month=1),
    },
}
```

## How It Works

### Data Collection

1. Users add their characters to the app (requires `esi-wallet.read_character_wallet.v1` scope)
2. The app periodically fetches wallet journal entries via ESI
3. Relevant entries (bounties, ESS, missions, incursions) are stored and taxed based on configuration
4. Tax amounts are calculated based on the system's security status and activity type

### Tax Calculation

Taxes are calculated using the following logic:
1. Check if the system is whitelisted/blacklisted
2. Determine the system's security status category
3. Apply the appropriate tax rate (security status rate takes precedence)
4. Store the tax amount with the journal entry

### Payment Processing

1. Admin characters monitor corp wallet journals
2. Payments with the configured phrase are detected
3. Credits are automatically applied to the paying character's balance

### Monthly Maintenance

1. Interest is applied to outstanding balances (if configured)
2. Notifications are sent to users with balances above the threshold
3. Discord notifications/DMs are sent (if configured)
4. Statistics are updated

## Permissions

- **basic_access**: Required to access the app and view own characters
- **admin_access**: Can add/manage admin characters and configure settings
- **auditor_access**: Can view all character data (for corp auditors)

## Support

For issues, feature requests, or questions:
- Create an issue on GitHub
- Join the Alliance Auth Discord server

## Credits

This app is based on and inspired by [aa-miningtaxes](https://gitlab.com/arctiru/aa-miningtaxes) by Arctiru.

## License

MIT License - See LICENSE file for details
