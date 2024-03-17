from pydantic import BaseModel
from enum import Enum
from typing import List, Optional


class VehicleType(str, Enum):
    bev = "bev"
    ice = "ice"


class Financing(BaseModel):
    loan: float
    interest: float
    maturity: int


class Consumption(BaseModel):
    commute: float
    highway: float


class Fees(BaseModel):
    service: float
    insurance: float


class FuelPrice(BaseModel):
    price: float
    inflation: float


class FuelInfo(BaseModel):
    commute: FuelPrice
    highway: FuelPrice


class Vehicle(BaseModel):
    model: str
    type: VehicleType
    price: float
    financing: Optional[Financing] = None
    consumption: Consumption
    fees: Fees
    depreciation: float
    fuel: FuelInfo


class Milage(BaseModel):
    commute: int
    highway: int


class Root(BaseModel):
    car: Vehicle
    compares: List[Vehicle]
    milage: Milage
