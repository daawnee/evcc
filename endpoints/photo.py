import azure.functions as func
import logging

from common import get_store


def photo(req: func.HttpRequest) -> func.HttpResponse:
    """Serve a car's hero photo (data/cars/<model_id>/photo.jpg)."""
    model_id = req.route_params.get("model_id", "")
    data = get_store().get_photo(model_id) if model_id else None
    if data is None:
        return func.HttpResponse("photo not found", status_code=404)
    return func.HttpResponse(
        data,
        headers={"Content-Type": "image/jpeg", "Cache-Control": "public, max-age=86400"},
    )
