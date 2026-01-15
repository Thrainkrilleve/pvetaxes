from django.core.management.base import BaseCommand

from pvetaxes.tasks import update_all_characters


class Command(BaseCommand):
    help = "Update wallet journals for all registered characters"

    def handle(self, *args, **options):
        self.stdout.write("Starting update for all characters...")
        result = update_all_characters()
        self.stdout.write(
            self.style.SUCCESS(
                f"Update complete: {result['success']}/{result['total']} succeeded, "
                f"{result['failed']} failed"
            )
        )
