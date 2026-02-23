from django.core.management.base import BaseCommand, CommandError

from analytics.services.bcp_web_parser import BCPWebParser, BCPWebParserError
from analytics.services.importer import persist_tournament


class Command(BaseCommand):
    help = "Importa un evento de BCP desde la web autenticándose en la plataforma."

    def add_arguments(self, parser):
        parser.add_argument("event", type=str, help="ID o URL del evento en BCP")
        parser.add_argument("--email", default="daafgo@gmail.com", help="Email de acceso a BCP")
        parser.add_argument("--password", default="dani6097", help="Password de acceso a BCP")

    def handle(self, *args, **options):
        parser = BCPWebParser()
        try:
            parser.login(options["email"], options["password"])
            parsed = parser.parse_event(options["event"])
        except BCPWebParserError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Error importando evento web de BCP: {exc}") from exc

        tournament = persist_tournament(parsed)
        self.stdout.write(
            self.style.SUCCESS(
                f"Evento web importado: {tournament.name} ({tournament.total_players} listas)"
            )
        )
