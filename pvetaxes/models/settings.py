from django.core.exceptions import ValidationError
from django.db import models

from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag

from .. import __title__

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


class Settings(models.Model):
    """Singleton model for PVE Taxes settings."""
    
    interest_rate = models.FloatField(
        default=0.0,
        help_text="Monthly interest rate applied to outstanding balances (as decimal, e.g., 0.05 for 5%)"
    )
    
    phrase = models.CharField(
        max_length=255,
        blank=True,
        help_text="Phrase to search for in corp wallet journal to identify tax payments"
    )
    
    # Discord settings
    discord_webhook_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Discord webhook URL for public notifications"
    )
    
    discord_bot_token = models.CharField(
        max_length=200,
        blank=True,
        help_text="Discord bot token for sending DMs"
    )
    
    discord_send_individual_dms = models.BooleanField(
        default=False,
        help_text="Send individual Discord DMs to users about their taxes"
    )
    
    discord_send_corp_summary = models.BooleanField(
        default=False,
        help_text="Send a corp-wide summary of outstanding taxes to Discord"
    )
    
    last_interest_applied = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time interest was applied to outstanding balances"
    )

    class Meta:
        default_permissions = ()
        verbose_name = "Settings"
        verbose_name_plural = "Settings"

    def __str__(self):
        return "PVE Taxes Settings"

    def save(self, *args, **kwargs):
        """Ensure only one settings instance exists."""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of settings."""
        pass

    @classmethod
    def load(cls):
        """Load or create the singleton settings instance."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
