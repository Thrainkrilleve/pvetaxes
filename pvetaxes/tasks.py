from celery import shared_task
from django.contrib.auth.models import User
from django.db import Error
from django.utils import timezone
from esi.errors import TokenError

from allianceauth.notifications import notify
from allianceauth.services.hooks import get_extension_logger

from .app_settings import (
    PVETAXES_PING_CURRENT_MSG,
    PVETAXES_PING_CURRENT_THRESHOLD,
    PVETAXES_PING_FIRST_MSG,
    PVETAXES_PING_INTEREST_APPLIED,
    PVETAXES_PING_SECOND_MSG,
    PVETAXES_PING_THRESHOLD,
    PVETAXES_TASKS_TIME_LIMIT,
)
from .helpers import (
    get_user_discord_id,
    send_corp_tax_summary,
    send_discord_dm,
    send_discord_notification,
)
from .models import AdminCharacter, Character, CharacterTaxCredits, Settings, Stats

logger = get_extension_logger(__name__)
TASK_DEFAULT_KWARGS = {"time_limit": PVETAXES_TASKS_TIME_LIMIT, "max_retries": 3}


def calctaxes():
    """Calculate taxes for all users."""
    s = Stats.load()
    return s.calctaxes()


@shared_task(**TASK_DEFAULT_KWARGS)
def update_character_wallet(character_pk: int):
    """Update wallet journal for a single character."""
    try:
        character = Character.objects.get(pk=character_pk)
        logger.info(f"Updating wallet journal for {character}")
        character.update_wallet_journal()
        character.calculate_monthly_totals()
        logger.info(f"Successfully updated wallet journal for {character}")
        return True
    except Character.DoesNotExist:
        logger.error(f"Character {character_pk} not found")
        return False
    except TokenError as e:
        logger.warning(f"Token error for character {character_pk}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error updating character {character_pk}: {e}", exc_info=True)
        return False


@shared_task(**TASK_DEFAULT_KWARGS)
def update_all_characters():
    """Update wallet journals for all registered characters."""
    logger.info("Starting update for all characters")
    
    characters = Character.objects.all()
    total = characters.count()
    success = 0
    failed = 0
    
    for character in characters:
        try:
            character.update_wallet_journal()
            character.calculate_monthly_totals()
            success += 1
        except TokenError as e:
            logger.warning(f"Token error for {character}: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"Error updating {character}: {e}", exc_info=True)
            failed += 1
    
    logger.info(f"Update complete: {success}/{total} succeeded, {failed} failed")
    
    # Update stats after all characters are updated
    update_stats.delay()
    
    return {"total": total, "success": success, "failed": failed}


@shared_task(**TASK_DEFAULT_KWARGS)
def update_admin_wallet(admin_pk: int):
    """Update corp wallet for a single admin character."""
    try:
        admin = AdminCharacter.objects.get(pk=admin_pk)
        logger.info(f"Updating corp wallet for {admin}")
        admin.update_corp_wallet()
        logger.info(f"Successfully updated corp wallet for {admin}")
        return True
    except AdminCharacter.DoesNotExist:
        logger.error(f"Admin character {admin_pk} not found")
        return False
    except TokenError as e:
        logger.warning(f"Token error for admin {admin_pk}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error updating admin {admin_pk}: {e}", exc_info=True)
        return False


@shared_task(**TASK_DEFAULT_KWARGS)
def update_all_admins():
    """Update corp wallets for all admin characters."""
    logger.info("Starting update for all admin characters")
    
    admins = AdminCharacter.objects.all()
    total = admins.count()
    success = 0
    failed = 0
    
    for admin in admins:
        try:
            admin.update_corp_wallet()
            success += 1
        except TokenError as e:
            logger.warning(f"Token error for {admin}: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"Error updating {admin}: {e}", exc_info=True)
            failed += 1
    
    logger.info(f"Admin update complete: {success}/{total} succeeded, {failed} failed")
    
    return {"total": total, "success": success, "failed": failed}


@shared_task(**TASK_DEFAULT_KWARGS)
def update_stats():
    """Update global statistics."""
    logger.info("Updating global statistics")
    try:
        stats = Stats.load()
        stats.update_stats()
        logger.info("Statistics updated successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating stats: {e}", exc_info=True)
        return False


@shared_task(**{**TASK_DEFAULT_KWARGS, **{"bind": True}})
def notify_taxes_due(self):
    """Send notifications to users about outstanding taxes."""
    settings = Settings.load()
    user2taxes = calctaxes()
    
    corp_summary_data = []
    
    for user in user2taxes.keys():
        total_owed, current_month = user2taxes[user]
        
        if total_owed > PVETAXES_PING_THRESHOLD:
            title = "PVE Taxes are due!"
            message = PVETAXES_PING_FIRST_MSG.format(total_owed / 1000000)
            notify(user=user, title=title, message=message, level="INFO")
            
            # Collect data for corp summary
            main_char = (
                user.profile.main_character.character_name
                if user.profile and user.profile.main_character
                else "N/A"
            )
            corp_summary_data.append({
                'username': user.username,
                'main_character': main_char,
                'balance': total_owed / 1000000  # Convert to millions
            })
            
            # Send individual Discord DM if enabled
            if settings.discord_send_individual_dms and settings.discord_bot_token:
                discord_id = get_user_discord_id(user)
                if discord_id:
                    dm_message = f"Hello! You currently owe {total_owed / 1000000:.2f} million ISK in PVE taxes. Please pay at your earliest convenience."
                    send_discord_dm(settings.discord_bot_token, discord_id, dm_message)
    
    # Send corp summary if enabled
    if settings.discord_send_corp_summary and settings.discord_webhook_url and corp_summary_data:
        send_corp_tax_summary(settings.discord_webhook_url, corp_summary_data)
    
    logger.info(f"Tax notifications sent to {len(corp_summary_data)} users")


@shared_task(**TASK_DEFAULT_KWARGS)
def apply_monthly_interest():
    """Apply interest to outstanding tax balances."""
    from datetime import datetime
    
    settings = Settings.load()
    
    if settings.interest_rate <= 0:
        logger.info("Interest rate is 0, skipping interest application")
        return
    
    # Check if interest was already applied this month
    now = timezone.now()
    if settings.last_interest_applied:
        last_applied = settings.last_interest_applied
        if last_applied.year == now.year and last_applied.month == now.month:
            logger.info("Interest already applied this month")
            return
    
    user2taxes = calctaxes()
    interest_applied_count = 0
    
    for user in user2taxes.keys():
        total_owed, _ = user2taxes[user]
        
        if total_owed <= 0:
            continue
        
        # Calculate interest
        interest_amount = total_owed * settings.interest_rate
        
        # Apply interest to all characters owned by this user
        characters = Character.objects.filter(
            eve_character__character_ownership__user=user
        )
        
        if characters.exists():
            # Apply to first character
            character = characters.first()
            CharacterTaxCredits.objects.create(
                character=character,
                amount=-interest_amount,  # Negative because it's a debit
                credit_type="interest",
                reason=f"Monthly interest ({settings.interest_rate * 100:.2f}%) applied to outstanding balance"
            )
            
            # Notify user
            title = "PVE Tax Interest Applied"
            message = PVETAXES_PING_INTEREST_APPLIED.format(interest_amount / 1000000)
            notify(user=user, title=title, message=message, level="WARNING")
            
            interest_applied_count += 1
    
    # Update last interest applied date
    settings.last_interest_applied = now
    settings.save()
    
    logger.info(f"Interest applied to {interest_applied_count} users")


@shared_task(**TASK_DEFAULT_KWARGS)
def run_monthly_tasks():
    """Run all monthly maintenance tasks."""
    logger.info("Running monthly maintenance tasks")
    
    # Apply interest
    apply_monthly_interest()
    
    # Send notifications
    notify_taxes_due()
    
    # Update stats
    update_stats()
    
    logger.info("Monthly maintenance tasks complete")


@shared_task(**TASK_DEFAULT_KWARGS)
def process_corp_payments():
    """Process tax payments from corp wallet entries."""
    from .models import AdminCorpWalletEntry
    from allianceauth.eveonline.models import EveCharacter
    
    logger.info("Processing corp wallet payments")
    
    # Get unprocessed payments
    entries = AdminCorpWalletEntry.objects.all()
    processed = 0
    
    for entry in entries:
        if not entry.second_party_id:
            continue
        
        try:
            # Find the character who made the payment
            eve_char = EveCharacter.objects.get(character_id=entry.second_party_id)
            
            # Find their PVE Taxes character
            try:
                character = Character.objects.get(eve_character=eve_char)
            except Character.DoesNotExist:
                logger.warning(f"No PVE Taxes character found for {eve_char}")
                continue
            
            # Apply credit
            CharacterTaxCredits.objects.create(
                character=character,
                amount=entry.amount,
                credit_type="payment",
                reason=f"Payment received: {entry.description}"
            )
            
            processed += 1
            
        except EveCharacter.DoesNotExist:
            logger.warning(f"Character {entry.second_party_id} not found")
            continue
        except Exception as e:
            logger.error(f"Error processing payment {entry.journal_id}: {e}", exc_info=True)
            continue
    
    logger.info(f"Processed {processed} payments")
    return processed
