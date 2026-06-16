import azure.functions as func
import json
import logging

from common import get_store


def models(req: func.HttpRequest) -> func.HttpResponse:
    """Return the catalog of available car models so a client can browse and pick them."""
    logging.info("Endpoint models processed a request.")

    store = get_store()

    return func.HttpResponse(
        json.dumps(store.get_index()),
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )
