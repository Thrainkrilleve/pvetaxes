from django.core.management.base import BaseCommand

from pvetaxes.tasks import update_stats


class Command(BaseCommand):
    help = "Update global PVE statistics"

    def handle(self, *args, **options):
        self.stdout.write("Updating statistics...")
        result = update_stats()
        
        if result:
            self.stdout.write(
                self.style.SUCCESS("Statistics updated successfully")
            )
        else:
            self.stdout.write(
                self.style.ERROR("Failed to update statistics")
            )
