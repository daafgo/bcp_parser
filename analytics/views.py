from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import render

from analytics.models import ArmyList, Tournament, UnitEntry


def dashboard(request):
    total_tournaments = Tournament.objects.count()
    total_lists = ArmyList.objects.count()
    unique_factions = ArmyList.objects.values("faction").distinct().count()

    top_factions = list(
        ArmyList.objects.values("faction")
        .annotate(list_count=Count("id"))
        .order_by("-list_count")[:10]
    )

    top_units = list(
        UnitEntry.objects.values("unit_name")
        .annotate(
            times_selected=Count("id"),
            total_models=Sum("quantity"),
            avg_points=Avg("points"),
        )
        .order_by("-times_selected")[:10]
    )

    faction_performance = list(
        ArmyList.objects.exclude(placing__isnull=True)
        .values("faction")
        .annotate(
            avg_placing=Avg("placing"),
            top10_finishes=Count("id", filter=Q(placing__lte=10)),
        )
        .order_by("avg_placing")[:10]
    )

    recent_tournaments = Tournament.objects.prefetch_related("army_lists").all()[:5]

    return render(
        request,
        "analytics/dashboard.html",
        {
            "total_tournaments": total_tournaments,
            "total_lists": total_lists,
            "unique_factions": unique_factions,
            "top_factions": top_factions,
            "top_units": top_units,
            "faction_performance": faction_performance,
            "recent_tournaments": recent_tournaments,
        },
    )
