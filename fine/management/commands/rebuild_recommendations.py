from django.core.management.base import BaseCommand

from fine.services.recommendations import generate_for_all_users


class Command(BaseCommand):
    help = "Rebuild recommendations for all users"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--batch-size", type=int, default=200)

    def handle(self, *args, **options):
        limit = options["limit"]
        batch_size = options["batch_size"]

        self.stdout.write(
            f"Start rebuilding recommendations: limit={limit}, batch_size={batch_size}"
        )
        generate_for_all_users(limit=limit, batch_size=batch_size)
        self.stdout.write(self.style.SUCCESS("Recommendations rebuilt successfully"))
