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
    type: VehicleType
    brand: str
    model: str
    price: float
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
