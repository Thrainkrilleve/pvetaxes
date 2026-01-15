# PVE Taxes - Installation & Usage Guide

## Overview

**PVE Taxes** is a new Alliance Auth app created to track and tax PVE activities including:
- **Bounties/Ratting** - ISK from killing NPCs
- **ESS Payouts** - Encounter Surveillance System payments
- **Missions** - Mission rewards and time bonuses
- **Incursions** - Incursion payout rewards

This app was created based on the Mining Taxes app structure but adapted to track wallet journal entries instead of mining ledgers.

## Key Differences from Mining Taxes

### Data Source
- **Mining Taxes**: Uses ESI mining ledger endpoint (`esi-industry.read_character_mining.v1`)
- **PVE Taxes**: Uses ESI wallet journal endpoint (`esi-wallet.read_character_wallet.v1`)

### Activities Tracked
- **Mining Taxes**: Ore types, ice, gas, moon mining
- **PVE Taxes**: Bounties, ESS, missions, incursions

### Tax Calculation
- **Mining Taxes**: Based on ore prices (refined vs raw) and location
- **PVE Taxes**: Based on ISK earned directly and system security status

## Installation Steps

### 1. Install the Package
```bash
cd /path/to/aa-pvetaxes
pip install -e .
```

### 2. Add to INSTALLED_APPS
Edit your `settings/local.py`:
```python
INSTALLED_APPS = [
    # ... existing apps
    'pvetaxes',
]
```

### 3. Configure URLs
In your main `urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    # ... existing patterns
    path('pvetaxes/', include('pvetaxes.urls')),
]
```

### 4. Run Migrations
```bash
python manage.py migrate pvetaxes
```

### 5. Create Migrations (First Time)
If migrations don't exist yet:
```bash
python manage.py makemigrations pvetaxes
python manage.py migrate pvetaxes
```

### 6. Restart Services
```bash
supervisorctl restart myauth:
```

## Configuration

### Basic Settings (settings/local.py)

```python
# Tax Rates by Activity Type
PVETAXES_TAX_BOUNTIES = 0.10  # 10%
PVETAXES_TAX_ESS = 0.10
PVETAXES_TAX_MISSIONS = 0.10
PVETAXES_TAX_INCURSIONS = 0.10

# Tax Rates by Security Status (overrides activity-specific)
PVETAXES_TAX_HISEC = 0.05
PVETAXES_TAX_LOSEC = 0.08
PVETAXES_TAX_NULLSEC = 0.10
PVETAXES_TAX_JSPACE = 0.12
PVETAXES_TAX_POCHVEN = 0.15

# Enable/Disable by Security
PVETAXES_TAX_HISEC_ENABLED = True
PVETAXES_TAX_LOSEC_ENABLED = True
PVETAXES_TAX_NULLSEC_ENABLED = True

# Interest Rate
PVETAXES_INTEREST_RATE = 0.02  # 2% per month

# Corp Wallet Settings
PVETAXES_CORP_WALLET_DIVISION = 1

# Discord Integration
PVETAXES_DISCORD_WEBHOOK_URL = ""
PVETAXES_DISCORD_BOT_TOKEN = ""
PVETAXES_DISCORD_SEND_INDIVIDUAL_DMS = False
PVETAXES_DISCORD_SEND_CORP_SUMMARY = False
```

### Celery Beat Tasks

Add these to your `CELERYBEAT_SCHEDULE`:

```python
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    'pvetaxes_update_all': {
        'task': 'pvetaxes.tasks.update_all_characters',
        'schedule': crontab(minute=0, hour='*/4'),  # Every 4 hours
    },
    'pvetaxes_update_admins': {
        'task': 'pvetaxes.tasks.update_all_admins',
        'schedule': crontab(minute=30),  # Every hour
    },
    'pvetaxes_update_stats': {
        'task': 'pvetaxes.tasks.update_stats',
        'schedule': crontab(minute=0, hour=6),  # Daily at 6 AM
    },
    'pvetaxes_monthly': {
        'task': 'pvetaxes.tasks.run_monthly_tasks',
        'schedule': crontab(minute=0, hour=12, day_of_month=1),  # 1st of month
    },
}
```

## Admin Setup

### 1. Grant Permissions

In Django Admin (`/admin/auth/group/`), grant these permissions to appropriate groups:
- `pvetaxes | general | Can access this app` - Basic user access
- `pvetaxes | general | Can set tax rates for groups and add accountant characters` - Admin access
- `pvetaxes | general | Can view all registered characters data` - Auditor access

### 2. Add Admin Characters

1. Go to Django Admin → PVE Taxes → Admin Characters
2. Click "Add Admin Character"
3. Select a character that has the **Accountant** role in their corporation
4. This character will be used to track corp wallet payments

### 3. Configure Settings

1. Go to Django Admin → PVE Taxes → Settings
2. Set the **Interest Rate** (e.g., 0.02 for 2% monthly)
3. Set the **Phrase** that users should include in payment descriptions
4. Configure Discord settings if desired

## Usage

### For Users

1. **Add Character**: Navigate to PVE Taxes → My Characters → Add Character
   - Requires ESI scope: `esi-wallet.read_character_wallet.v1`

2. **View Activity**: Check the dashboard to see:
   - Current month earnings by activity type
   - Tax amounts owed
   - Payment history

3. **Make Payments**: 
   - Send ISK to corp master wallet
   - Include the configured phrase in the description
   - Payment will be automatically credited

### Management Commands

```bash
# Update all characters
python manage.py pvetaxes_update_all

# Update specific character
python manage.py pvetaxes_update_character <id>

# Update statistics
python manage.py pvetaxes_update_stats

# Run monthly tasks (interest, notifications)
python manage.py pvetaxes_monthly_tasks

# Zero all balances (WARNING: Irreversible!)
python manage.py pvetaxes_zero_balances --confirm
```

## File Structure

```
aa-pvetaxes/
├── pvetaxes/
│   ├── __init__.py                 # App initialization
│   ├── admin.py                    # Django admin configuration
│   ├── app_settings.py             # Settings definitions
│   ├── apps.py                     # App configuration
│   ├── auth_hooks.py               # Alliance Auth integration
│   ├── decorators.py               # View decorators
│   ├── forms.py                    # Django forms
│   ├── helpers.py                  # Helper functions
│   ├── providers.py                # ESI client provider
│   ├── tasks.py                    # Celery tasks
│   ├── urls.py                     # URL routing
│   ├── views.py                    # View functions
│   ├── management/
│   │   └── commands/               # Management commands
│   │       ├── pvetaxes_update_all.py
│   │       ├── pvetaxes_update_character.py
│   │       ├── pvetaxes_update_stats.py
│   │       ├── pvetaxes_monthly_tasks.py
│   │       └── pvetaxes_zero_balances.py
│   ├── migrations/                 # Database migrations
│   │   └── __init__.py
│   ├── models/                     # Database models
│   │   ├── __init__.py
│   │   ├── admin.py                # Admin character models
│   │   ├── character.py            # Character & journal models
│   │   ├── general.py              # Permissions model
│   │   ├── settings.py             # Settings model
│   │   └── stats.py                # Statistics model
│   └── templates/
│       └── pvetaxes/               # HTML templates
│           ├── base.html
│           ├── index.html
│           ├── launcher.html
│           ├── user_summary.html
│           ├── user_ledger.html
│           ├── character_viewer.html
│           ├── admin_launcher.html
│           ├── admin_tables.html
│           ├── faq.html
│           └── error.html
├── setup.py                        # Package setup
├── setup.cfg                       # Setup configuration
├── MANIFEST.in                     # Package manifest
├── LICENSE                         # MIT License
├── README.md                       # User documentation
└── CHANGELOG.md                    # Version history
```

## Database Models

### Character
- Tracks individual characters
- Stores lifetime taxes and credits
- JSON fields for monthly breakdowns

### CharacterWalletJournalEntry
- Individual wallet journal entries
- Links to character, solar system
- Stores activity type, amount, tax rate, tax amount

### CharacterTaxCredits
- Credits/debits applied to characters
- Types: credit, debit, payment, interest, adjustment
- Automatically updates character's lifetime credits

### AdminCharacter
- Corporate accountant characters
- Used to track corp wallet for payments

### AdminCorpWalletEntry
- Corp wallet journal entries
- Used to identify tax payments

### Settings
- Singleton configuration model
- Interest rate, payment phrase, Discord settings

### Stats
- Singleton statistics model
- Current month and lifetime totals
- Leaderboards by activity type

## ESI Scopes Required

### For Users (Characters)
- `esi-wallet.read_character_wallet.v1` - Read character wallet journal

### For Admins (Admin Characters)
- `esi-wallet.read_corporation_wallets.v1` - Read corp wallet journal

## Troubleshooting

### Characters Not Updating
1. Check ESI token is valid
2. Verify character has correct ESI scope
3. Check Celery is running: `supervisorctl status`
4. Check logs: `tail -f /var/log/myauth/celery.log`

### Payments Not Being Credited
1. Verify payment includes the configured phrase
2. Check admin character has valid token
3. Verify admin character has Accountant role
4. Run: `python manage.py pvetaxes_update_all`

### Tax Rates Not Applying
1. Check `PVETAXES_TAX_*_ENABLED` settings
2. Verify system is not blacklisted
3. Check if whitelist is empty or includes the system
4. Review tax rate calculation in helpers.py

## Support & Development

This app is based on the Mining Taxes app structure. If you encounter issues:

1. Check the logs for error messages
2. Verify all ESI tokens are valid
3. Ensure Celery beat is running for periodic tasks
4. Review the README.md for configuration options

## Credits

Based on [aa-miningtaxes](https://gitlab.com/arctiru/aa-miningtaxes) by Arctiru.
