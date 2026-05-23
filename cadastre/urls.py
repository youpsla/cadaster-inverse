from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("communes/", views.communes, name="communes"),
    path("search/", views.search, name="search"),
    path(
        "departement/<slug:dep_slug>/",
        views.departement,
        name="departement",
    ),
    path(
        "departement/<slug:dep_slug>/<slug:commune_slug>/",
        views.commune,
        name="commune",
    ),
]
