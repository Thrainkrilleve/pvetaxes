import datetime as dt
from typing import Optional

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.functional import cached_property
from django.utils.timezone import now
from esi.errors import TokenError
from esi.models import Token
from eveuniverse.models import EveSolarSystem

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger
from app_utils.allianceauth import notify_throttled
from app_utils.caching import ObjectCacheMixin
from app_utils.logging import LoggerAddTag

from .. import __title__
from ..app_settings import (
    PVETAXES_UPDATE_LEDGER_STALE,
    PVETAXES_UPDATE_STALE_OFFSET,
)
from ..decorators import fetch_token_for_character
from ..providers import esi

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


class CharacterQuerySet(models.QuerySet):
    def eve_character_ids(self) -> set:
        return set(self.values_list("eve_character__character_id", flat=True))

    def owned_by_user(self, user: User) -> models.QuerySet:
        """Filter characters owned by user."""
        return self.filter(eve_character__character_ownership__user__pk=user.pk)


class CharacterManagerBase(ObjectCacheMixin, models.Manager):
    def unregistered_characters_of_user_count(self, user: User) -> int:
        return CharacterOwnership.objects.filter(
            user=user, character__pvetaxes_character__isnull=True
        ).count()


CharacterManager = CharacterManagerBase.from_queryset(CharacterQuerySet)


class CharacterAbstract(models.Model):
    id = models.AutoField(primary_key=True)
    eve_character = models.OneToOneField(
        EveCharacter, related_name="pvetaxes_character", on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    objects = CharacterManager()

    class Meta:
        abstract = True
        default_permissions = ()

    def __str__(self) -> str:
        return f"{self.eve_character.character_name} (PK:{self.pk})"

    def __repr__(self) -> str:
        return f"Character(pk={self.pk}, eve_character='{self.eve_character}')"

    @cached_property
    def name(self) -> str:
        return self.eve_character.character_name

    @cached_property
    def character_ownership(self) -> Optional[CharacterOwnership]:
        try:
            return self.eve_character.character_ownership
        except ObjectDoesNotExist:
            return None

    @cached_property
    def user(self) -> Optional[User]:
        try:
            return self.character_ownership.user
        except AttributeError:
            return None

    @cached_property
    def main_character(self) -> Optional[EveCharacter]:
        try:
            return self.character_ownership.user.profile.main_character
        except AttributeError:
            return None

    @cached_property
    def is_main(self) -> bool:
        """returns True if this character is a main character, else False"""
        try:
            return self.main_character.character_id == self.eve_character.character_id
        except AttributeError:
            return False

    def fetch_token(self, scopes=None) -> Token:
        """returns valid token for character

        Args:
        - scopes: Optionally provide the required scopes.
        Otherwise will use all scopes defined for this character.

        Exceptions:
        - TokenError: If no valid token can be found
        """
        if self.is_orphan:
            raise TokenError(
                f"Can not find token for orphaned character: {self}"
            ) from None
        token = (
            Token.objects.prefetch_related("scopes")
            .filter(user=self.user, character_id=self.eve_character.character_id)
            .require_scopes(scopes if scopes else self.get_esi_scopes())
            .require_valid()
            .first()
        )
        if not token:
            message_id = f"{__title__}-fetch_token-{self.pk}-TokenError"
            title = f"{__title__}: Invalid or missing token for {self.eve_character}"
            message = (
                f"PVE Taxes could not find a valid token for your "
                f"character {self.eve_character}.\n"
                f"Please re-add that character to PVE Taxes "
                "at your earliest convenience to update your token."
            )
            notify_throttled(
                message_id=message_id, user=self.user, title=title, message=message
            )
            raise TokenError(f"Could not find a matching token for {self}")
        return token

    @cached_property
    def is_orphan(self) -> bool:
        """Whether this character is not owned by a user."""
        return self.character_ownership is None

    def user_is_owner(self, user: User) -> bool:
        """Return True if the given user is owner of this character"""
        try:
            return self.user == user
        except AttributeError:
            return False

    @classmethod
    def update_time_until_stale(cls) -> dt.timedelta:
        minutes = PVETAXES_UPDATE_LEDGER_STALE
        return dt.timedelta(minutes=minutes - PVETAXES_UPDATE_STALE_OFFSET)

    def get_esi_scopes(self):
        """Return the ESI scopes required for this character."""
        return ["esi-wallet.read_character_wallet.v1"]


class Character(CharacterAbstract):
    """Represents a character being tracked for PVE taxation."""
    
    life_credits = models.FloatField(default=0.0)
    """Total lifetime credits applied to this character"""
    
    life_taxes = models.FloatField(default=0.0)
    """Total lifetime taxes owed by this character"""
    
    monthly_activity_json = models.JSONField(default=dict, null=True, blank=True)
    """Monthly breakdown of PVE activity (bounties, ESS, missions, incursions)"""
    
    monthly_taxes_json = models.JSONField(default=dict, null=True, blank=True)
    """Monthly breakdown of taxes owed"""
    
    monthly_credits_json = models.JSONField(default=dict, null=True, blank=True)
    """Monthly breakdown of credits applied"""
    
    last_wallet_update = models.DateTimeField(null=True, blank=True)
    """Last time the wallet journal was updated"""

    @fetch_token_for_character("esi-wallet.read_character_wallet.v1")
    def update_wallet_journal(self, token: Token):
        """Update wallet journal from ESI for this character."""
        logger.info("%s: Fetching wallet journal from ESI", self)
        
        # Fetch wallet journal entries
        # ESI reference types for PVE activities:
        # bounty_prizes = Bounties from ratting
        # ess_escrow_transfer = ESS payouts
        # agent_mission_reward = Mission rewards
        # agent_mission_time_bonus_reward = Mission time bonus
        # corporate_reward_payout = Incursion payouts
        
        entries = esi.client.Wallet.get_characters_character_id_wallet_journal(
            character_id=self.eve_character.character_id,
            token=token.valid_access_token(),
        ).results()
        
        relevant_ref_types = [
            "bounty_prizes",
            "ess_escrow_transfer",
            "agent_mission_reward",
            "agent_mission_time_bonus_reward",
            "corporate_reward_payout",
        ]
        
        for entry in entries:
            if entry["ref_type"] not in relevant_ref_types:
                continue
            
            # Determine activity type
            if entry["ref_type"] == "bounty_prizes":
                activity_type = "bounty"
            elif entry["ref_type"] == "ess_escrow_transfer":
                activity_type = "ess"
            elif entry["ref_type"] in ["agent_mission_reward", "agent_mission_time_bonus_reward"]:
                activity_type = "mission"
            elif entry["ref_type"] == "corporate_reward_payout":
                activity_type = "incursion"
            else:
                continue
            
            # Check if entry already exists
            try:
                journal_entry = self.wallet_journal.get(journal_id=entry["id"])
                # Entry exists, skip
                continue
            except CharacterWalletJournalEntry.DoesNotExist:
                # Create new entry
                solar_system = None
                if "solar_system_id" in entry:
                    solar_system, _ = EveSolarSystem.objects.get_or_create_esi(
                        id=entry["solar_system_id"]
                    )
                
                journal_entry = self.wallet_journal.create(
                    journal_id=entry["id"],
                    date=entry["date"],
                    amount=entry.get("amount", 0),
                    ref_type=entry["ref_type"],
                    activity_type=activity_type,
                    eve_solar_system=solar_system,
                    description=entry.get("description", ""),
                )
                journal_entry.calculate_tax()
        
        self.last_wallet_update = now()
        self.save()
        logger.info("%s: Wallet journal update complete", self)

    def calculate_monthly_totals(self):
        """Calculate monthly activity and tax totals."""
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth
        
        # Group by month and activity type
        monthly_data = (
            self.wallet_journal
            .annotate(month=TruncMonth("date"))
            .values("month", "activity_type")
            .annotate(
                total_amount=Sum("amount"),
                total_tax=Sum("tax_amount")
            )
            .order_by("month", "activity_type")
        )
        
        # Build JSON structures
        activity_json = {}
        taxes_json = {}
        
        for entry in monthly_data:
            month_key = entry["month"].strftime("%Y-%m")
            if month_key not in activity_json:
                activity_json[month_key] = {}
                taxes_json[month_key] = {}
            
            activity_type = entry["activity_type"]
            activity_json[month_key][activity_type] = float(entry["total_amount"])
            taxes_json[month_key][activity_type] = float(entry["total_tax"])
        
        self.monthly_activity_json = activity_json
        self.monthly_taxes_json = taxes_json
        self.save()


class CharacterWalletJournalEntry(models.Model):
    """Individual wallet journal entry for PVE activity."""
    
    character = models.ForeignKey(
        Character, related_name="wallet_journal", on_delete=models.CASCADE
    )
    journal_id = models.BigIntegerField(unique=True, db_index=True)
    """ESI journal entry ID"""
    
    date = models.DateTimeField(db_index=True)
    """Date of the activity"""
    
    amount = models.FloatField()
    """ISK amount earned"""
    
    ref_type = models.CharField(max_length=100)
    """ESI reference type"""
    
    activity_type = models.CharField(max_length=50, db_index=True)
    """Activity type: bounty, ess, mission, incursion"""
    
    eve_solar_system = models.ForeignKey(
        EveSolarSystem, on_delete=models.SET_NULL, null=True, blank=True
    )
    """Solar system where activity occurred"""
    
    description = models.TextField(blank=True)
    """Description from journal entry"""
    
    tax_amount = models.FloatField(default=0.0)
    """Tax amount calculated for this entry"""
    
    tax_rate = models.FloatField(default=0.0)
    """Tax rate applied (as decimal)"""
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["character", "date"]),
            models.Index(fields=["activity_type", "date"]),
        ]

    def __str__(self):
        return f"{self.character.name} - {self.activity_type} - {self.amount:,.0f} ISK"

    def calculate_tax(self):
        """Calculate and save the tax amount for this entry."""
        from ..helpers import get_tax_rate_for_system
        
        if self.eve_solar_system:
            self.tax_rate = get_tax_rate_for_system(
                self.eve_solar_system.id, self.activity_type
            )
        else:
            from ..app_settings import PVETAXES_UNKNOWN_TAX_RATE
            self.tax_rate = PVETAXES_UNKNOWN_TAX_RATE
        
        self.tax_amount = self.amount * self.tax_rate
        self.save()


class CharacterTaxCredits(models.Model):
    """Tax credits/debits applied to a character."""
    
    CREDIT_TYPES = [
        ("credit", "Credit"),
        ("debit", "Debit"),
        ("payment", "Payment"),
        ("interest", "Interest"),
        ("adjustment", "Adjustment"),
    ]
    
    character = models.ForeignKey(
        Character, related_name="tax_credits", on_delete=models.CASCADE
    )
    amount = models.FloatField()
    """Amount of credit/debit (positive for credit, negative for debit)"""
    
    credit_type = models.CharField(max_length=20, choices=CREDIT_TYPES, default="credit")
    reason = models.TextField()
    """Reason for the credit/debit"""
    
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.character.name} - {self.credit_type} - {self.amount:,.0f} ISK"

    def save(self, *args, **kwargs):
        """Update character's lifetime credits when saving."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self.character.life_credits += self.amount
            self.character.save()
