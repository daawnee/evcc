import azure.functions as func
import logging
import os

# Built Vue app lives in ui/dist (repo root / ui / dist).
UI_DIST = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "ui", "dist"))

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".map": "application/json",
}


def static_files(req: func.HttpRequest) -> func.HttpResponse:
    """Serve the built single-page app. Real asset paths map to files under ui/dist; everything
    else falls back to index.html so the SPA can handle client-side routing."""
    path = (req.route_params.get("path") or "").strip("/")
    if not path:
        path = "index.html"

    candidate = os.path.normpath(os.path.join(UI_DIST, path))
    # Guard against path traversal outside the dist dir.
    if not candidate.startswith(UI_DIST):
        return func.HttpResponse("forbidden", status_code=403)

    if not os.path.isfile(candidate):
        candidate = os.path.join(UI_DIST, "index.html")
        if not os.path.isfile(candidate):
            return func.HttpResponse(
                "UI not built yet. Run `npm install && npm run build` in ui/.",
                status_code=404,
            )

    with open(candidate, "rb") as f:
        body = f.read()
    ext = os.path.splitext(candidate)[1].lower()
    ctype = _CONTENT_TYPES.get(ext, "application/octet-stream")
    return func.HttpResponse(body, headers={"Content-Type": ctype})
