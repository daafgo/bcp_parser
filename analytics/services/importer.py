from django.db import transaction

from analytics.models import ArmyList, Tournament, UnitEntry
from analytics.services.bcp_parser import ParsedTournament


@transaction.atomic
def persist_tournament(parsed: ParsedTournament) -> Tournament:
    tournament, _ = Tournament.objects.update_or_create(
        bcp_tournament_id=parsed.bcp_tournament_id,
        defaults={
            "name": parsed.name,
            "event_date": parsed.event_date,
            "game_system": parsed.game_system,
            "total_players": len(parsed.army_lists),
        },
    )

    tournament.army_lists.all().delete()

    for parsed_list in parsed.army_lists:
        army_list = ArmyList.objects.create(
            tournament=tournament,
            player_name=parsed_list.player_name,
            faction=parsed_list.faction,
            subfaction=parsed_list.subfaction,
            placing=parsed_list.placing,
            battle_points=parsed_list.battle_points,
        )
        UnitEntry.objects.bulk_create(
            [
                UnitEntry(
                    army_list=army_list,
                    unit_name=u.unit_name,
                    quantity=u.quantity,
                    points=u.points,
                    battlefield_role=u.battlefield_role,
                )
                for u in parsed_list.units
            ]
        )

    return tournament
