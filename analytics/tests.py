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

    @patch.object(BCPWebParser, "_get_html")
    def test_parse_event_walks_roster_and_downloads_lists(self, get_html):
        roster_html = """
        <html><head><title>Sample GT | Best Coast Pairings</title></head><body>
          <a href="/list/AAA111">Roster 1</a>
          <a href="/list/BBB222">Roster 2</a>
        </body></html>
        """
        list_1 = """
        <html><body>
          <div>Player: Alice</div>
          <div>Faction: Aeldari</div>
          <pre>2 Warp Spiders - 95 pts\n1 Farseer - 80 pts</pre>
        </body></html>
        """
        list_2 = """
        <html><body>
          <div>Player: Bob</div>
          <div>Faction: Space Marines</div>
          <pre>1 Redemptor Dreadnought - 210 pts</pre>
        </body></html>
        """

        get_html.side_effect = [roster_html, list_1, list_2]

        parser = BCPWebParser()
        parsed = parser.parse_event("MvspHPzDhDpr")

        self.assertEqual(parsed.bcp_tournament_id, "MvspHPzDhDpr")
        self.assertEqual(parsed.name, "Sample GT")
        self.assertEqual(len(parsed.army_lists), 2)
        self.assertEqual(parsed.army_lists[0].player_name, "Alice")
        self.assertEqual(parsed.army_lists[1].faction, "Space Marines")

        self.assertEqual(get_html.call_count, 3)


class DashboardViewTests(TestCase):
    def test_dashboard_loads(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard de composiciones")
