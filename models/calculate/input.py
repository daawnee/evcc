from pydantic import BaseModel, model_validator
from enum import Enum
from functools import cache
from resources import defaults
from typing import List, Optional, Dict, Any


class VehicleType(str, Enum):
    bev = "bev"
    petrol = "petrol"
    diesel = "diesel"


class Financing(BaseModel):
    loan: float
    rate: float
    months: int

    @cache
    def monthly(self) -> float:
        return (
            (self.rate / 12)
            * (1 / (1 - (1 + self.rate / 12) ** (-self.months)))
            * self.loan
        )

    @cache
    def total(self) -> float:
        return self.monthly * self.months

    @cache
    def total_interest(self) -> float:
        return self.total - self.loan


class Consumption(BaseModel):
    average: float
    highway: float


class Fees(BaseModel):
    service: float
    insurance: float


class FuelPrice(BaseModel):
    price: float
    inflation: float


class FuelInfo(BaseModel):
    average: FuelPrice
    highway: FuelPrice


class Depreciation(BaseModel):
    year: int
    value: float


class Vehicle(BaseModel):
    type: VehicleType
    brand: str
    model: str
    price: float
    depreciation: Optional[List[Depreciation]] = None
    fuel: Optional[FuelInfo] = None
    financing: Optional[Financing] = None
    consumption: Optional[Consumption] = None
    fees: Optional[Fees] = None

    @model_validator(mode="after")
    def validate(self) -> "Vehicle":
        if self.depreciation is None:
            self.depreciation = defaults.depreciation[self.type]
        if self.fuel is None:
            self.fuel = defaults.fuel[self.type]
        return self


class Milage(BaseModel):
    commute: int
    highway: int


class Root(BaseModel):
    car: Vehicle
    compares: List[Vehicle]
    milage: Optional[Milage] = None

    @model_validator(mode="after")
    def validate(self) -> "Root":
        if self.milage is None:
            self.milage = defaults.milage
        return self
