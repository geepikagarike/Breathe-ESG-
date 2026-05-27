from django.core.management.base import BaseCommand

from ingest.demo import seed_demo


class Command(BaseCommand):
    help = "Load demo tenant, factors, connectors, and sample ingestions."

    def add_arguments(self, parser):
        parser.add_argument("--no-reset", action="store_true", help="Keep existing activity and batches.")

    def handle(self, *args, **options):
        tenant, batches = seed_demo(reset=not options["no_reset"])
        self.stdout.write(self.style.SUCCESS(f"Seeded {tenant.slug} with {len(batches)} batches."))

