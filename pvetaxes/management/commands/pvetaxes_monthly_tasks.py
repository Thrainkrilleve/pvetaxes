from django.core.management.base import BaseCommand

from pvetaxes.tasks import run_monthly_tasks


class Command(BaseCommand):
    help = "Run monthly maintenance tasks (interest, notifications, etc.)"

    def handle(self, *args, **options):
        self.stdout.write("Running monthly maintenance tasks...")
        run_monthly_tasks()
        self.stdout.write(
            self.style.SUCCESS("Monthly maintenance tasks complete")
        )
