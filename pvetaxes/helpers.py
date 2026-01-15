"""Helper functions for PVE Taxes"""
import datetime as dt
import requests

from django.utils import timezone
from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag

from . import __title__

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


def get_security_status_category(security_status: float) -> str:
    """Return the security status category for a given security status value."""
    if security_status >= 0.5:
        return "hisec"
    elif security_status > 0.0:
        return "losec"
    elif security_status <= 0.0 and security_status > -0.99:
        return "nullsec"
    elif security_status == -1.0:
        return "jspace"
    else:
        return "unknown"


def is_pochven_system(solar_system_id: int) -> bool:
    """Check if a solar system is in Pochven."""
    # Pochven region ID is 10000070
    from eveuniverse.models import EveSolarSystem
    try:
        system = EveSolarSystem.objects.get(id=solar_system_id)
        return system.eve_constellation.eve_region_id == 10000070
    except Exception:
        return False


def get_tax_rate_for_system(solar_system_id: int, activity_type: str = None) -> float:
    """
    Calculate the tax rate for a given solar system and activity type.
    
    Args:
        solar_system_id: The solar system ID
        activity_type: Type of activity (bounty, ess, mission, incursion)
    
    Returns:
        The applicable tax rate as a decimal (e.g., 0.10 for 10%)
    """
    from .app_settings import (
        PVETAXES_TAX_HISEC,
        PVETAXES_TAX_LOSEC,
        PVETAXES_TAX_NULLSEC,
        PVETAXES_TAX_JSPACE,
        PVETAXES_TAX_POCHVEN,
        PVETAXES_TAX_HISEC_ENABLED,
        PVETAXES_TAX_LOSEC_ENABLED,
        PVETAXES_TAX_NULLSEC_ENABLED,
        PVETAXES_TAX_JSPACE_ENABLED,
        PVETAXES_TAX_POCHVEN_ENABLED,
        PVETAXES_WHITELIST,
        PVETAXES_BLACKLIST,
        PVETAXES_UNKNOWN_TAX_RATE,
    )
    from eveuniverse.models import EveSolarSystem
    
    # Check whitelist/blacklist
    if PVETAXES_WHITELIST and solar_system_id not in PVETAXES_WHITELIST:
        return 0.0
    if solar_system_id in PVETAXES_BLACKLIST:
        return 0.0
    
    try:
        system = EveSolarSystem.objects.get(id=solar_system_id)
        
        # Check for Pochven
        if is_pochven_system(solar_system_id):
            return PVETAXES_TAX_POCHVEN if PVETAXES_TAX_POCHVEN_ENABLED else 0.0
        
        # Get security status category
        sec_status = system.security_status
        category = get_security_status_category(sec_status)
        
        # Apply tax rates based on security status
        if category == "hisec":
            return PVETAXES_TAX_HISEC if PVETAXES_TAX_HISEC_ENABLED else 0.0
        elif category == "losec":
            return PVETAXES_TAX_LOSEC if PVETAXES_TAX_LOSEC_ENABLED else 0.0
        elif category == "nullsec":
            return PVETAXES_TAX_NULLSEC if PVETAXES_TAX_NULLSEC_ENABLED else 0.0
        elif category == "jspace":
            return PVETAXES_TAX_JSPACE if PVETAXES_TAX_JSPACE_ENABLED else 0.0
        else:
            return PVETAXES_UNKNOWN_TAX_RATE
    except Exception as e:
        logger.warning(f"Error getting tax rate for system {solar_system_id}: {e}")
        return PVETAXES_UNKNOWN_TAX_RATE


def get_user_discord_id(user):
    """Get a user's Discord ID from their profile."""
    try:
        from allianceauth.services.modules.discord.models import DiscordUser
        discord_user = DiscordUser.objects.filter(user=user).first()
        if discord_user:
            return discord_user.uid
    except Exception as e:
        logger.warning(f"Error getting Discord ID for user {user}: {e}")
    return None


def send_discord_notification(webhook_url: str, message: str, title: str = None):
    """Send a notification to a Discord channel via webhook."""
    if not webhook_url:
        return False
    
    try:
        payload = {"content": message}
        if title:
            payload = {
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": 3447003  # Blue color
                }]
            }
        
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")
        return False


def send_discord_dm(bot_token: str, user_id: str, message: str):
    """Send a DM to a Discord user via bot."""
    if not bot_token or not user_id:
        return False
    
    try:
        # Create DM channel
        headers = {"Authorization": f"Bot {bot_token}"}
        dm_response = requests.post(
            "https://discord.com/api/v10/users/@me/channels",
            headers=headers,
            json={"recipient_id": user_id}
        )
        dm_response.raise_for_status()
        channel_id = dm_response.json()["id"]
        
        # Send message
        msg_response = requests.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers=headers,
            json={"content": message}
        )
        msg_response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Error sending Discord DM to {user_id}: {e}")
        return False


def send_corp_tax_summary(webhook_url: str, summary_data: list):
    """Send a formatted table of outstanding taxes to Discord."""
    if not webhook_url or not summary_data:
        return False
    
    try:
        # Sort by balance descending
        summary_data.sort(key=lambda x: x['balance'], reverse=True)
        
        # Create formatted message
        message = "**Outstanding PVE Taxes Summary**\n```\n"
        message += f"{'User':<20} {'Main Character':<30} {'Balance (M ISK)':>15}\n"
        message += "-" * 65 + "\n"
        
        total = 0
        for entry in summary_data:
            username = entry['username'][:19]
            main_char = entry['main_character'][:29]
            balance = entry['balance']
            total += balance
            message += f"{username:<20} {main_char:<30} {balance:>15.2f}\n"
        
        message += "-" * 65 + "\n"
        message += f"{'TOTAL':<51} {total:>15.2f}\n"
        message += "```"
        
        return send_discord_notification(webhook_url, message, "PVE Taxes Summary")
    except Exception as e:
        logger.error(f"Error sending corp tax summary: {e}")
        return False
