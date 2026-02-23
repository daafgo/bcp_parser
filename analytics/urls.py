from django.urls import path

from analytics.views import dashboard

urlpatterns = [
    path("", dashboard, name="dashboard"),
]
