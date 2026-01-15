from django.urls import path

from . import views

app_name = "pvetaxes"

urlpatterns = [
    path("", views.index, name="index"),
    path("launcher/", views.launcher, name="launcher"),
    path("admin_launcher/", views.admin_launcher, name="admin_launcher"),
    path("admin_tables/", views.admin_tables, name="admin_tables"),
    path("user_summary/", views.user_summary, name="user_summary"),
    path("user_ledger/<int:character_id>/", views.user_ledger, name="user_ledger"),
    path("character_viewer/<int:character_id>/", views.character_viewer, name="character_viewer"),
    path("faq/", views.faq, name="faq"),
]
