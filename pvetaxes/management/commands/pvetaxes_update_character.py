from django.core.management.base import BaseCommand

from pvetaxes.models import Character
from pvetaxes.tasks import update_character_wallet


class Command(BaseCommand):
    help = "Update wallet journal for a specific character"

    def add_arguments(self, parser):
        parser.add_argument(
            "character_id",
            type=int,
            help="Character ID to update"
        )

    def handle(self, *args, **options):
        character_id = options["character_id"]
        
        try:
            character = Character.objects.get(pk=character_id)
            self.stdout.write(f"Updating {character}...")
            
            result = update_character_wallet(character_id)
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully updated {character}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"Failed to update {character}")
                )
        except Character.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Character {character_id} not found")
            )
