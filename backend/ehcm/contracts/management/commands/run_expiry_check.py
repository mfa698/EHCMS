from django.core.management.base import BaseCommand
from contracts.tasks import evaluate_contract_expiries


class Command(BaseCommand):
    help = "Runs the 90/60/30-day contract expiry check immediately."

    def handle(self, *args, **options):
        _ = (args, options)
        count = evaluate_contract_expiries()
        self.stdout.write(self.style.SUCCESS(f"Expiry check complete. Triggered {count} new alert(s)."))
