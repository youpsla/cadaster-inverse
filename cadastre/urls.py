from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("communes/", views.communes, name="communes"),
    path("search/", views.search, name="search"),
]
