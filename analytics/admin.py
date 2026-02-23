from django.contrib import admin

from analytics.models import ArmyList, Tournament, UnitEntry


class UnitEntryInline(admin.TabularInline):
    model = UnitEntry
    extra = 0


@admin.register(ArmyList)
class ArmyListAdmin(admin.ModelAdmin):
    list_display = ("player_name", "faction", "subfaction", "placing", "tournament")
    list_filter = ("faction", "tournament")
    search_fields = ("player_name", "faction", "subfaction")
    inlines = [UnitEntryInline]


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "event_date", "game_system", "total_players")
    search_fields = ("name", "bcp_tournament_id")


@admin.register(UnitEntry)
class UnitEntryAdmin(admin.ModelAdmin):
    list_display = ("unit_name", "quantity", "points", "battlefield_role", "army_list")
    list_filter = ("battlefield_role",)
    search_fields = ("unit_name",)
