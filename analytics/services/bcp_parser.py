from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(slots=True)
class ParsedUnit:
    unit_name: str
    quantity: int
    points: int
    battlefield_role: str


@dataclass(slots=True)
class ParsedArmyList:
    player_name: str
    faction: str
    subfaction: str
    placing: int | None
    battle_points: float
    units: list[ParsedUnit]


@dataclass(slots=True)
class ParsedTournament:
    bcp_tournament_id: str
    name: str
    event_date: date
    game_system: str
    army_lists: list[ParsedArmyList]


def parse_bcp_export(path: str | Path) -> ParsedTournament:
    """
    Parsea un export simplificado de Best Coast Pairings en formato JSON.

    Estructura esperada:
    {
      "tournament_id": "abc-123",
      "name": "GT Madrid",
      "event_date": "2025-05-18",
      "game_system": "Warhammer 40k",
      "lists": [
        {
          "player_name": "Alice",
          "faction": "Adeptus Custodes",
          "subfaction": "Shield Host",
          "placing": 1,
          "battle_points": 95,
          "units": [
            {"unit_name": "Custodian Guard", "quantity": 3, "points": 180, "battlefield_role": "Battleline"}
          ]
        }
      ]
    }
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    army_lists: list[ParsedArmyList] = []

    for item in payload.get("lists", []):
        units = [
            ParsedUnit(
                unit_name=unit["unit_name"],
                quantity=int(unit.get("quantity", 1)),
                points=int(unit.get("points", 0)),
                battlefield_role=unit.get("battlefield_role", ""),
            )
            for unit in item.get("units", [])
        ]
        army_lists.append(
            ParsedArmyList(
                player_name=item["player_name"],
                faction=item["faction"],
                subfaction=item.get("subfaction", ""),
                placing=item.get("placing"),
                battle_points=float(item.get("battle_points", 0)),
                units=units,
            )
        )

    return ParsedTournament(
        bcp_tournament_id=payload["tournament_id"],
        name=payload["name"],
        event_date=date.fromisoformat(payload["event_date"]),
        game_system=payload.get("game_system", "Warhammer 40k"),
        army_lists=army_lists,
    )
