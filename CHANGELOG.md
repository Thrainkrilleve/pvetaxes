# Version 1.0.0

## Initial Release

### Features
- Track PVE activities: bounties/ratting, ESS payouts, missions, and incursions
- Configurable tax rates by activity type and security status
- Support for multiple corporations
- Tax credit system for adjustments
- Monthly interest on outstanding balances
- Discord integration (webhooks, DMs, corp summaries)
- Monthly leaderboards by activity type
- User dashboard for viewing activity and taxes
- Admin interface for managing characters and settings
- Auditor access for viewing all character data
- Whitelist/blacklist system support
- Management commands for automation
- Celery tasks for periodic updates

### Technical Details
- Based on aa-miningtaxes structure
- Tracks wallet journal entries via ESI
- Supports security status-based taxation
- Automatic payment processing from corp wallet
- Monthly maintenance tasks via Celery Beat
