from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import index as sitemap_index, sitemap as sitemap_section
from django.views.generic import TemplateView

from cadastre.sitemaps import sitemaps

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("cadastre.urls")),
    path(
        "robots.txt",
        TemplateView.as_view(
            template_name="cadastre/robots.txt", content_type="text/plain"
        ),
    ),
    path(
        "sitemap.xml",
        sitemap_index,
        {"sitemaps": sitemaps},
        name="sitemap-index",
    ),
    path(
        "sitemap-<section>.xml",
        sitemap_section,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
]
