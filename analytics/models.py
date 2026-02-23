from django.db import models


class Tournament(models.Model):
    bcp_tournament_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    event_date = models.DateField()
    game_system = models.CharField(max_length=100, default="Warhammer 40k")
    total_players = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-event_date", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.event_date})"


class ArmyList(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="army_lists")
    player_name = models.CharField(max_length=150)
    faction = models.CharField(max_length=120)
    subfaction = models.CharField(max_length=120, blank=True)
    placing = models.PositiveIntegerField(null=True, blank=True)
    battle_points = models.FloatField(default=0)

    class Meta:
        ordering = ["placing", "player_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tournament", "player_name", "faction"],
                name="unique_player_faction_per_tournament",
            )
        ]

    def __str__(self) -> str:
        return f"{self.player_name} - {self.faction}"


class UnitEntry(models.Model):
    army_list = models.ForeignKey(ArmyList, on_delete=models.CASCADE, related_name="units")
    unit_name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(default=1)
    points = models.PositiveIntegerField(default=0)
    battlefield_role = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["unit_name"]

    def __str__(self) -> str:
        return f"{self.unit_name} x{self.quantity}"
