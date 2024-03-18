from pydantic import BaseModel
from enum import Enum
from functools import cache
from typing import List, Optional


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


class Amortization(BaseModel):
    year: int
    value: float


class Vehicle(BaseModel):
    type: VehicleType
    brand: str
    model: str
    price: float
    amortization: Optional[List[Amortization]] = None
    financing: Optional[Financing] = None
    consumption: Optional[Consumption] = None
    fees: Optional[Fees] = None
    depreciation: Optional[float] = None
    fuel: Optional[FuelInfo] = None


class Milage(BaseModel):
    commute: int
    highway: int


class Root(BaseModel):
    car: Vehicle
    compares: List[Vehicle]
    milage: Optional[Milage] = None
