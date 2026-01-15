import datetime as dt
from typing import Optional

from django.db import models
from django.utils.timezone import now
from esi.errors import TokenError
from esi.models import Token
from eveuniverse.models import EveSolarSystem

from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger
from app_utils.logging import LoggerAddTag

from .. import __title__
from ..decorators import fetch_token_for_character
from ..providers import esi

logger = LoggerAddTag(get_extension_logger(__name__), __title__)


class AdminCharacter(models.Model):
    """Corporate accountant character for tracking corp wallet and activities."""
    
    id = models.AutoField(primary_key=True)
    eve_character = models.OneToOneField(
        EveCharacter, related_name="pvetaxes_admin", on_delete=models.CASCADE
    )
    corporation = models.ForeignKey(
        EveCorporationInfo, on_delete=models.CASCADE, related_name="pvetaxes_admins"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        default_permissions = ()

    def __str__(self) -> str:
        return f"{self.eve_character.character_name} ({self.corporation.corporation_name})"

    def fetch_token(self, scopes=None) -> Token:
        """Fetch a valid token for this admin character."""
        required_scopes = scopes or [
            "esi-wallet.read_corporation_wallets.v1",
        ]
        
        try:
            ownership = self.eve_character.character_ownership
            token = (
                Token.objects.prefetch_related("scopes")
                .filter(
                    user=ownership.user,
                    character_id=self.eve_character.character_id
                )
                .require_scopes(required_scopes)
                .require_valid()
                .first()
            )
            if not token:
                raise TokenError(f"No valid token found for {self}")
            return token
        except Exception as e:
            logger.error(f"Error fetching token for {self}: {e}")
            raise TokenError(f"Could not fetch token for {self}") from e

    @fetch_token_for_character("esi-wallet.read_corporation_wallets.v1")
    def update_corp_wallet(self, token: Token):
        """Update corporation wallet journal for tracking tax payments."""
        from ..app_settings import PVETAXES_CORP_WALLET_DIVISION
        from .settings import Settings
        
        logger.info("%s: Fetching corp wallet journal from ESI", self)
        
        settings = Settings.load()
        search_phrase = settings.phrase.lower() if settings.phrase else ""
        
        entries = esi.client.Wallet.get_corporations_corporation_id_wallets_division_journal(
            corporation_id=self.corporation.corporation_id,
            division=PVETAXES_CORP_WALLET_DIVISION,
            token=token.valid_access_token(),
        ).results()
        
        for entry in entries:
            # Look for payment entries matching our search phrase
            if entry["ref_type"] != "player_donation":
                continue
            
            description = entry.get("description", "").lower()
            if search_phrase and search_phrase not in description:
                continue
            
            # Check if entry already exists
            try:
                wallet_entry = self.corp_wallet_entries.get(journal_id=entry["id"])
                continue
            except AdminCorpWalletEntry.DoesNotExist:
                # Create new entry
                second_party_id = entry.get("second_party_id")
                
                wallet_entry = self.corp_wallet_entries.create(
                    journal_id=entry["id"],
                    date=entry["date"],
                    amount=entry.get("amount", 0),
                    second_party_id=second_party_id,
                    description=entry.get("description", ""),
                )
        
        self.last_update = now()
        self.save()
        logger.info("%s: Corp wallet update complete", self)


class AdminCorpWalletEntry(models.Model):
    """Corporation wallet entry for tracking tax payments."""
    
    admin_character = models.ForeignKey(
        AdminCharacter, related_name="corp_wallet_entries", on_delete=models.CASCADE
    )
    journal_id = models.BigIntegerField(unique=True, db_index=True)
    date = models.DateTimeField(db_index=True)
    amount = models.FloatField()
    second_party_id = models.IntegerField(null=True, blank=True)
    """Character ID of the person who made the payment"""
    
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["admin_character", "date"]),
        ]

    def __str__(self):
        return f"{self.admin_character.corporation.corporation_name} - {self.amount:,.0f} ISK"
