from __future__ import annotations

import json
import re
from datetime import date, datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from analytics.services.bcp_parser import ParsedArmyList, ParsedTournament, ParsedUnit


class BCPWebParserError(RuntimeError):
    pass


class BCPWebParser:
    BASE_URL = "https://www.bestcoastpairings.com"

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def login(self, email: str, password: str) -> None:
        login_page = self.session.get(urljoin(self.BASE_URL, "/login"), timeout=30)
        login_page.raise_for_status()

        payload = {"email": email, "password": password}
        response = self.session.post(
            urljoin(self.BASE_URL, "/login"),
            data=payload,
            timeout=30,
            allow_redirects=True,
        )
        response.raise_for_status()

        if "login" in response.url.lower() and "logout" not in response.text.lower():
            raise BCPWebParserError("No se pudo autenticar en Best Coast Pairings.")

    def parse_event(self, event_id_or_url: str) -> ParsedTournament:
        event_url = self._build_event_url(event_id_or_url)
        response = self.session.get(event_url, timeout=30)
        response.raise_for_status()

        next_data = self._extract_next_data(response.text)
        if next_data is None:
            raise BCPWebParserError(
                "No se encontró JSON estructurado del evento en la página."
            )

        return self._parse_next_data(next_data, event_id_or_url)

    def _build_event_url(self, event_id_or_url: str) -> str:
        if event_id_or_url.startswith("http://") or event_id_or_url.startswith("https://"):
            return event_id_or_url
        return urljoin(self.BASE_URL, f"/event/{event_id_or_url}")

    def _extract_next_data(self, html: str) -> dict | None:
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            return json.loads(script.string)

        for sc in soup.find_all("script"):
            content = sc.string or sc.text or ""
            if "__NEXT_DATA__" in content:
                match = re.search(r"__NEXT_DATA__\s*=\s*(\{.*\})", content, flags=re.DOTALL)
                if match:
                    return json.loads(match.group(1))
        return None

    def _parse_next_data(self, next_data: dict, fallback_id: str) -> ParsedTournament:
        event_node = self._find_first(next_data, ["event", "tournament", "data"]) or {}
        lists_node = self._find_first(next_data, ["lists", "armyLists", "players"]) or []

        event_id = str(event_node.get("id") or event_node.get("eventId") or fallback_id)
        name = event_node.get("name") or event_node.get("title") or f"Event {event_id}"
        raw_date = event_node.get("eventDate") or event_node.get("date") or date.today().isoformat()
        parsed_date = self._parse_date(raw_date)

        army_lists: list[ParsedArmyList] = []
        for item in lists_node:
            units_data = item.get("units") or item.get("entries") or []
            units: list[ParsedUnit] = [
                ParsedUnit(
                    unit_name=str(u.get("name") or u.get("unit") or "Unknown Unit"),
                    quantity=int(u.get("quantity", 1) or 1),
                    points=int(float(u.get("points", 0) or 0)),
                    battlefield_role=str(u.get("role") or u.get("battlefieldRole") or ""),
                )
                for u in units_data
            ]

            army_lists.append(
                ParsedArmyList(
                    player_name=str(item.get("playerName") or item.get("name") or "Unknown Player"),
                    faction=str(item.get("faction") or item.get("armyFaction") or "Unknown Faction"),
                    subfaction=str(item.get("subfaction") or item.get("detachment") or ""),
                    placing=self._to_int_or_none(item.get("placing") or item.get("rank")),
                    battle_points=float(item.get("battlePoints") or item.get("points") or 0),
                    units=units,
                )
            )

        return ParsedTournament(
            bcp_tournament_id=event_id,
            name=name,
            event_date=parsed_date,
            game_system="Warhammer 40k",
            army_lists=army_lists,
        )

    def _find_first(self, node: object, keys: list[str]):
        if isinstance(node, dict):
            for key in keys:
                if key in node:
                    return node[key]
            for value in node.values():
                found = self._find_first(value, keys)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = self._find_first(value, keys)
                if found is not None:
                    return found
        return None

    def _parse_date(self, value: str) -> date:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return date.today()

    def _to_int_or_none(self, value) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
