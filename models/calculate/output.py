from pydantic import BaseModel
from typing import List, Optional

from .input import VehicleType


class MonthlyPoint(BaseModel):
    """One month of the TCO curve. Component fields are the cost incurred *in* that month;
    ``cumulative`` is the running total cost of ownership up to and including that month."""

    month: int
    depreciation: float
    energy: float
    service: float
    insurance: float
    other: float  # tax + parking + vignette
    financing: float  # interest portion of financing, spread over the loan term
    total: float  # sum of the component costs for this month
    cumulative: float


class CarResult(BaseModel):
    model_id: str
    make: str
    model: str
    type: VehicleType
    photo: Optional[str] = None
    series: List[MonthlyPoint]


class Breakeven(BaseModel):
    """First month within the horizon where the cumulative-cost ordering of the two cars flips.
    ``month`` is null when the curves never cross within the projection horizon."""

    car_a: str
    car_b: str
    month: Optional[int] = None


class Root(BaseModel):
    cars: List[CarResult]
    breakevens: List[Breakeven]
