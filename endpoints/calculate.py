import azure.functions as func
import logging

from common import Params, get_store
from models.calculate import (
    CarData,
    Input,
    Output,
    apply_overrides,
    engine,
    fallback_car_data,
)
from pydantic import ValidationError


def _text(body: str, status: int = 400) -> func.HttpResponse:
    return func.HttpResponse(
        body,
        headers={"Content-Type": "text/plain; charset=UTF-8"},
        status_code=status,
    )


def calculate(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Endpoint calculate processed a request.")

    params = Params(req)

    try:
        request = Input(**params.body)
    except ValidationError as e:
        return _text(str(e))

    store = get_store()
    results = []

    for sel in request.cars:
        raw = store.get_car(sel.model_id)
        if raw is not None:
            car = CarData(**raw)
        elif sel.type is not None:
            car = fallback_car_data(sel.type, model_id=sel.model_id)
        else:
            return _text(
                f"Unknown model_id '{sel.model_id}' and no 'type' override provided to fall back on."
            )

        car = apply_overrides(car, sel)
        results.append(engine.compute(sel.model_id, car, sel, request.assumptions))

    output = Output(cars=results, breakevens=engine.breakevens(results))

    return func.HttpResponse(
        output.model_dump_json(),
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )
