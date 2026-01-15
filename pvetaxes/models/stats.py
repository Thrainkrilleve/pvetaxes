import datetime as dt
import json
from collections import defaultdict

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum
from django.utils.timezone import now

from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag

from .. import __title__

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


class Stats(models.Model):
    """Statistics tracking for PVE activities."""
    
    # Current month activity by activity type
    curmonth_bounties = models.FloatField(default=0.0)
    curmonth_ess = models.FloatField(default=0.0)
    curmonth_missions = models.FloatField(default=0.0)
    curmonth_incursions = models.FloatField(default=0.0)
    
    # Current month taxes by activity type
    curmonth_bounties_tax = models.FloatField(default=0.0)
    curmonth_ess_tax = models.FloatField(default=0.0)
    curmonth_missions_tax = models.FloatField(default=0.0)
    curmonth_incursions_tax = models.FloatField(default=0.0)
    
    # Lifetime totals
    life_bounties = models.FloatField(default=0.0)
    life_ess = models.FloatField(default=0.0)
    life_missions = models.FloatField(default=0.0)
    life_incursions = models.FloatField(default=0.0)
    
    # Lifetime taxes
    life_bounties_tax = models.FloatField(default=0.0)
    life_ess_tax = models.FloatField(default=0.0)
    life_missions_tax = models.FloatField(default=0.0)
    life_incursions_tax = models.FloatField(default=0.0)
    
    # Leader data (JSON)
    curmonth_leadergraph = models.JSONField(default=dict, blank=True)
    """Top earners for current month by activity type"""
    
    user_activity_ledger_90day = models.JSONField(default=dict, blank=True)
    """90-day activity history by user"""
    
    admin_get_all_activity_json = models.JSONField(default=dict, blank=True)
    """Admin view of all activity"""
    
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ()
        verbose_name = "Statistics"
        verbose_name_plural = "Statistics"

    def __str__(self):
        return f"PVE Stats (Updated: {self.last_update})"

    @classmethod
    def load(cls):
        """Load or create the singleton stats instance."""
        obj, created = cls.objects.get_or_create(pk=1)
        if created:
            obj.update_stats()
        return obj

    def save(self, *args, **kwargs):
        """Ensure only one stats instance exists."""
        self.pk = 1
        super().save(*args, **kwargs)

    def update_stats(self):
        """Recalculate all statistics."""
        from .character import Character, CharacterWalletJournalEntry
        
        logger.info("Updating PVE statistics")
        
        # Get current month start
        today = now()
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Current month stats
        current_month_entries = CharacterWalletJournalEntry.objects.filter(
            date__gte=month_start
        )
        
        self.curmonth_bounties = current_month_entries.filter(
            activity_type="bounty"
        ).aggregate(Sum("amount"))["amount__sum"] or 0.0
        
        self.curmonth_ess = current_month_entries.filter(
            activity_type="ess"
        ).aggregate(Sum("amount"))["amount__sum"] or 0.0
        
        self.curmonth_missions = current_month_entries.filter(
            activity_type="mission"
        ).aggregate(Sum("amount"))["amount__sum"] or 0.0
        
        self.curmonth_incursions = current_month_entries.filter(
            activity_type="incursion"
        ).aggregate(Sum("amount"))["amount__sum"] or 0.0
        
        # Current month taxes
        self.curmonth_bounties_tax = current_month_entries.filter(
            activity_type="bounty"
        ).aggregate(Sum("tax_amount"))["tax_amount__sum"] or 0.0
        
        self.curmonth_ess_tax = current_month_entries.filter(
            activity_type="ess"
        ).aggregate(Sum("tax_amount"))["tax_amount__sum"] or 0.0
        
        self.curmonth_missions_tax = current_month_entries.filter(
            activity_type="mission"
        ).aggregate(Sum("tax_amount"))["tax_amount__sum"] or 0.0
        
        self.curmonth_incursions_tax = current_month_entries.filter(
            activity_type="incursion"
        ).aggregate(Sum("tax_amount"))["tax_amount__sum"] or 0.0
        
        # Lifetime stats
        all_entries = CharacterWalletJournalEntry.objects.all()
        
        self.life_bounties = all_entries.filter(
            activity_type="bounty"
        ).aggregate(Sum("amount"))["amount__sum"] or 0.0
        
        self.life_ess = all_entries.filter(
            activity_type="ess"
        ).aggregate(Sum("amount"))["amount__sum"] or 0.0
        
        self.life_missions = all_entries.filter(
            activity_type="mission"
        ).aggregate(Sum("amount"))["amount__sum"] or 0.0
        
        self.life_incursions = all_entries.filter(
            activity_type="incursion"
        ).aggregate(Sum("amount"))["amount__sum"] or 0.0
        
        # Lifetime taxes
        self.life_bounties_tax = all_entries.filter(
            activity_type="bounty"
        ).aggregate(Sum("tax_amount"))["tax_amount__sum"] or 0.0
        
        self.life_ess_tax = all_entries.filter(
            activity_type="ess"
        ).aggregate(Sum("tax_amount"))["tax_amount__sum"] or 0.0
        
        self.life_missions_tax = all_entries.filter(
            activity_type="mission"
        ).aggregate(Sum("tax_amount"))["tax_amount__sum"] or 0.0
        
        self.life_incursions_tax = all_entries.filter(
            activity_type="incursion"
        ).aggregate(Sum("tax_amount"))["tax_amount__sum"] or 0.0
        
        # Update leaderboards
        self.update_leaderboards()
        
        self.save()
        logger.info("PVE statistics updated")

    def update_leaderboards(self):
        """Update leaderboard data."""
        from .character import Character, CharacterWalletJournalEntry
        from django.db.models import Sum
        
        # Get current month start
        today = now()
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Current month leaderboard
        leaderboard = {}
        
        for activity_type in ["bounty", "ess", "mission", "incursion"]:
            top_users = (
                CharacterWalletJournalEntry.objects
                .filter(date__gte=month_start, activity_type=activity_type)
                .values("character__eve_character__character_name")
                .annotate(total=Sum("amount"))
                .order_by("-total")[:10]
            )
            
            leaderboard[activity_type] = [
                {
                    "name": entry["character__eve_character__character_name"],
                    "amount": entry["total"]
                }
                for entry in top_users
            ]
        
        self.curmonth_leadergraph = leaderboard

    def calctaxes(self):
        """Calculate outstanding tax balances for all users.
        
        Returns:
            dict: {User: (total_owed, current_month_owed)}
        """
        from .character import Character, CharacterTaxCredits
        
        user_taxes = {}
        
        # Get all characters
        for character in Character.objects.select_related("eve_character__character_ownership__user"):
            user = character.user
            if not user:
                continue
            
            # Calculate lifetime taxes owed
            lifetime_taxes = character.wallet_journal.aggregate(
                Sum("tax_amount")
            )["tax_amount__sum"] or 0.0
            
            # Calculate lifetime credits
            lifetime_credits = character.life_credits
            
            # Calculate current month taxes
            today = now()
            month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            current_month_taxes = character.wallet_journal.filter(
                date__gte=month_start
            ).aggregate(Sum("tax_amount"))["tax_amount__sum"] or 0.0
            
            # Net balance
            net_balance = lifetime_taxes - lifetime_credits
            
            # Add to user total (in case they have multiple characters)
            if user in user_taxes:
                user_taxes[user] = (
                    user_taxes[user][0] + net_balance,
                    user_taxes[user][1] + current_month_taxes
                )
            else:
                user_taxes[user] = (net_balance, current_month_taxes)
        
        return user_taxes
