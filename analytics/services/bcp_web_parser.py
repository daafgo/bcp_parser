from __future__ import annotations

import json
import re
from datetime import date, datetime
from urllib.parse import parse_qs, urljoin, urlparse

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
        event_html = self._get_html(event_url)

        event_name, event_date = self._parse_event_metadata(event_html, event_id_or_url)
        list_urls = self._extract_list_urls(event_html, event_url)

        if not list_urls:
            raise BCPWebParserError("No se encontraron listas en el roster del evento.")

        parsed_lists: list[ParsedArmyList] = []
        for list_url in list_urls:
            list_html = self._get_html(list_url)
            parsed_lists.append(self._parse_list_page(list_html, list_url))

        return ParsedTournament(
            bcp_tournament_id=self._extract_event_id(event_id_or_url),
            name=event_name,
            event_date=event_date,
            game_system="Warhammer 40k",
            army_lists=parsed_lists,
        )

    def _build_event_url(self, event_id_or_url: str) -> str:
        if event_id_or_url.startswith("http://") or event_id_or_url.startswith("https://"):
            parsed = urlparse(event_id_or_url)
            qs = parse_qs(parsed.query)
            if qs.get("active_tab", [""])[0] != "roster":
                sep = "&" if parsed.query else "?"
                return f"{event_id_or_url}{sep}active_tab=roster"
            return event_id_or_url
        return urljoin(self.BASE_URL, f"/event/{event_id_or_url}?active_tab=roster")

    def _get_html(self, url: str) -> str:
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def _parse_event_metadata(self, event_html: str, event_id_or_url: str) -> tuple[str, date]:
        next_data = self._extract_next_data(event_html)
        event_node = self._find_first(next_data, ["event", "tournament", "data"]) if next_data else None
        if isinstance(event_node, dict):
            name = event_node.get("name") or event_node.get("title")
            raw_date = event_node.get("eventDate") or event_node.get("date")
            if name:
                return str(name), self._parse_date(str(raw_date or date.today().isoformat()))

        soup = BeautifulSoup(event_html, "html.parser")
        title_tag = soup.find("title")
        page_title = title_tag.get_text(strip=True) if title_tag else ""
        event_name = page_title.split("|")[0].strip() if page_title else f"Event {self._extract_event_id(event_id_or_url)}"
        return event_name, date.today()

    def _extract_list_urls(self, event_html: str, event_url: str) -> list[str]:
        soup = BeautifulSoup(event_html, "html.parser")
        urls: set[str] = set()

        for anchor in soup.select('a[href*="/list/"]'):
            href = anchor.get("href")
            if not href:
                continue
            urls.add(urljoin(self.BASE_URL, href))

        next_data = self._extract_next_data(event_html)
        if next_data:
            for token in self._find_list_ids(next_data):
                urls.add(urljoin(self.BASE_URL, f"/list/{token}"))

        return sorted(urls)

    def _find_list_ids(self, node: object) -> set[str]:
        results: set[str] = set()
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = key.lower()
                if lowered in {"listid", "list_id", "rosterid", "roster_id"} and value:
                    results.add(str(value))
                if isinstance(value, str) and "/list/" in value:
                    match = re.search(r"/list/([A-Za-z0-9]+)", value)
                    if match:
                        results.add(match.group(1))
                results |= self._find_list_ids(value)
        elif isinstance(node, list):
            for item in node:
                results |= self._find_list_ids(item)
        return results

    def _parse_list_page(self, list_html: str, list_url: str) -> ParsedArmyList:
        soup = BeautifulSoup(list_html, "html.parser")
        next_data = self._extract_next_data(list_html)

        player_name = "Unknown Player"
        faction = "Unknown Faction"
        subfaction = ""
        placing = None
        battle_points = 0.0
        units: list[ParsedUnit] = []

        if next_data:
            list_node = self._find_first(next_data, ["list", "roster", "armyList", "listData"])
            if isinstance(list_node, dict):
                player_name = str(list_node.get("playerName") or list_node.get("name") or player_name)
                faction = str(list_node.get("faction") or list_node.get("armyFaction") or faction)
                subfaction = str(list_node.get("subfaction") or list_node.get("detachment") or subfaction)
                placing = self._to_int_or_none(list_node.get("placing") or list_node.get("rank"))
                battle_points = float(list_node.get("battlePoints") or list_node.get("points") or 0)

                units_data = list_node.get("units") or list_node.get("entries") or []
                for u in units_data:
                    units.append(
                        ParsedUnit(
                            unit_name=str(u.get("name") or u.get("unit") or "Unknown Unit"),
                            quantity=int(u.get("quantity", 1) or 1),
                            points=int(float(u.get("points", 0) or 0)),
                            battlefield_role=str(u.get("role") or u.get("battlefieldRole") or ""),
                        )
                    )

        if not units:
            units = self._parse_units_from_text(soup.get_text("\n", strip=True))

        if player_name == "Unknown Player":
            player_name = self._extract_by_label(soup, ["Player", "Jugador"], default=player_name)
        if faction == "Unknown Faction":
            faction = self._extract_by_label(soup, ["Faction", "Facción"], default=faction)

        return ParsedArmyList(
            player_name=player_name,
            faction=faction,
            subfaction=subfaction,
            placing=placing,
            battle_points=battle_points,
            units=units,
        )

    def _extract_by_label(self, soup: BeautifulSoup, labels: list[str], default: str) -> str:
        text = soup.get_text("\n", strip=True)
        for label in labels:
            match = re.search(rf"{re.escape(label)}\s*[:\-]\s*([^\n]+)", text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return default

    def _parse_units_from_text(self, text: str) -> list[ParsedUnit]:
        units: list[ParsedUnit] = []
        patterns = [
            re.compile(r"^(?P<qty>\d+)x?\s+(?P<name>.+?)\s+[\-–]\s*(?P<pts>\d+)\s*(pts?|points?)$", re.IGNORECASE),
            re.compile(r"^(?P<name>.+?)\s+x(?P<qty>\d+)\s+[\-–]\s*(?P<pts>\d+)\s*(pts?|points?)$", re.IGNORECASE),
        ]

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            for regex in patterns:
                match = regex.match(line)
                if match:
                    units.append(
                        ParsedUnit(
                            unit_name=match.group("name").strip(),
                            quantity=int(match.group("qty")),
                            points=int(match.group("pts")),
                            battlefield_role="",
                        )
                    )
                    break
        return units

    def _extract_event_id(self, event_id_or_url: str) -> str:
        if event_id_or_url.startswith("http://") or event_id_or_url.startswith("https://"):
            match = re.search(r"/event/([A-Za-z0-9]+)", event_id_or_url)
            if match:
                return match.group(1)
        return event_id_or_url

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
