from django.contrib import admin
from django.conf import settings
from django.http import FileResponse, Http404
from django.urls import include, path
from django.urls import re_path


FRONTEND_DIST = settings.BASE_DIR.parent / "frontend" / "dist"


def frontend_index(_request):
    index_path = FRONTEND_DIST / "index.html"
    if not index_path.exists():
        raise Http404("Frontend build not found")
    return FileResponse(index_path.open("rb"), content_type="text/html")


def frontend_asset(_request, asset_path):
    requested = (FRONTEND_DIST / "assets" / asset_path).resolve()
    assets_root = (FRONTEND_DIST / "assets").resolve()
    if not str(requested).startswith(str(assets_root)) or not requested.exists():
        raise Http404("Asset not found")
    return FileResponse(requested.open("rb"))

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("ingest.urls")),
    re_path(r"^assets/(?P<asset_path>.+)$", frontend_asset),
    re_path(r"^$", frontend_index),
    re_path(r"^(?!api/|admin/).*$", frontend_index),
]
