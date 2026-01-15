from django.core.management.base import BaseCommand
from django.db import models

from pvetaxes.models import Character, CharacterWalletJournalEntry, CharacterTaxCredits


class Command(BaseCommand):
    help = "Zero out all character balances (WARNING: This is irreversible!)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirm that you want to zero all balances"
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    "This command will zero out all character balances.\n"
                    "Run with --confirm to proceed."
                )
            )
            return
        
        self.stdout.write("Zeroing all character balances...")
        
        for character in Character.objects.all():
            # Calculate current balance
            lifetime_taxes = character.wallet_journal.aggregate(
                total=models.Sum("tax_amount")
            )["total"] or 0
            
            lifetime_credits = character.life_credits
            balance = lifetime_taxes - lifetime_credits
            
            if balance != 0:
                # Add offsetting credit
                CharacterTaxCredits.objects.create(
                    character=character,
                    amount=balance,
                    credit_type="adjustment",
                    reason="Balance zeroed by admin"
                )
                self.stdout.write(f"Zeroed {character}: {balance:,.2f} ISK")
        
        self.stdout.write(
            self.style.SUCCESS("All character balances zeroed")
        )
