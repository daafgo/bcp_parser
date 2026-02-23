import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from analytics.models import ArmyList, Tournament, UnitEntry
from analytics.services.bcp_web_parser import BCPWebParser


class ImportBCPCommandTests(TestCase):
    def test_import_creates_tournament_lists_and_units(self):
        sample_json = """
        {
          "tournament_id": "evt-001",
          "name": "Barcelona Team Championship",
          "event_date": "2025-04-13",
          "lists": [
            {
              "player_name": "Carlos",
              "faction": "Astra Militarum",
              "placing": 2,
              "battle_points": 88,
              "units": [
                {"unit_name": "Leman Russ", "quantity": 2, "points": 170, "battlefield_role": "Vehicle"}
              ]
            }
          ]
        }
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.json"
            file_path.write_text(sample_json, encoding="utf-8")
            call_command("import_bcp_lists", str(file_path))

        self.assertEqual(Tournament.objects.count(), 1)
        self.assertEqual(ArmyList.objects.count(), 1)
        self.assertEqual(UnitEntry.objects.count(), 1)


class ImportBCPWebCommandTests(TestCase):
    @patch("analytics.management.commands.import_bcp_event.BCPWebParser")
    def test_import_web_event_persists_data(self, parser_cls):
        parsed = MagicMock()
        parsed.bcp_tournament_id = "web-123"
        parsed.name = "Web Event"
        from datetime import date

        parsed.event_date = date(2025, 1, 1)
        parsed.game_system = "Warhammer 40k"
        parsed.army_lists = []

        parser = parser_cls.return_value
        parser.parse_event.return_value = parsed

        call_command("import_bcp_event", "web-123")

        parser.login.assert_called_once_with("daafgo@gmail.com", "dani6097")
        parser.parse_event.assert_called_once_with("web-123")
        self.assertTrue(Tournament.objects.filter(bcp_tournament_id="web-123").exists())


class BCPWebParserTests(TestCase):
    def test_extracts_next_data_payload(self):
        html = """
        <html><head></head><body>
        <script id="__NEXT_DATA__" type="application/json">{"props": {"pageProps": {"event": {"id": "abc", "name": "GT", "eventDate": "2025-06-01"}, "lists": []}}}</script>
        </body></html>
        """

        parser = BCPWebParser()
        payload = parser._extract_next_data(html)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["props"]["pageProps"]["event"]["id"], "abc")


class DashboardViewTests(TestCase):
    def test_dashboard_loads(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard de composiciones")
