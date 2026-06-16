import azure.functions as func
import json
import logging

from common import get_store


def car(req: func.HttpRequest) -> func.HttpResponse:
    """Return one car's full metadata (CarData) by model_id — used by the UI for price prefill
    and to display the selected car's specs."""
    model_id = req.route_params.get("model_id", "")
    data = get_store().get_car(model_id) if model_id else None
    if data is None:
        return func.HttpResponse("car not found", status_code=404)
    return func.HttpResponse(
        json.dumps(data),
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )
