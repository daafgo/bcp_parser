from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from analytics.services.bcp_parser import parse_bcp_export
from analytics.services.importer import persist_tournament


class Command(BaseCommand):
    help = "Importa listas de ejército de Best Coast Pairings desde un JSON local."

    def add_arguments(self, parser):
        parser.add_argument("source", type=str, help="Ruta al archivo JSON exportado")

    def handle(self, *args, **options):
        source = Path(options["source"])
        if not source.exists():
            raise CommandError(f"El archivo no existe: {source}")

        parsed = parse_bcp_export(source)
        tournament = persist_tournament(parsed)

        self.stdout.write(
            self.style.SUCCESS(
                f"Importación completada: {tournament.name} ({tournament.total_players} listas)"
            )
        )
