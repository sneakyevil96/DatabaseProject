"""URL patterns for the pizzeria app."""

from django.urls import path

from . import views

app_name = "pizzeria"

urlpatterns = [
    path("menu/", views.menu_view, name="menu"),
]
