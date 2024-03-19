from pydantic import BaseModel, model_validator
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
    tax: float
    service: float
    insurance: float
    parking: float
    vignette: float


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
            self.depreciation = depreciation[self.type]
        if self.fuel is None:
            self.fuel = fuel[self.type]
        if consumption is None:
            self.consumption = consumption[self.type]
        if fees is None:
            self.fees = fees[self.type]
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
            self.milage = milage
        return self


### Defaults ###

# https://holtankoljak.hu/
fuel = {
    VehicleType.petrol: FuelInfo(
        average=FuelPrice(price=618.8, inflation=5.0),
        highway=FuelPrice(price=708.9, inflation=5.0),
    ),
    VehicleType.diesel: FuelInfo(
        average=FuelPrice(price=642.1, inflation=5.0),
        highway=FuelPrice(price=722.9, inflation=5.0),
    ),
    VehicleType.bev: FuelInfo(
        average=FuelPrice(price=72.0, inflation=5.0),
        highway=FuelPrice(price=225.0, inflation=5.0),
    ),
}


# https://villanyautosok.hu/2021/04/18/ennyi-uzemanyagot-fustolnek-el-a-magyar-autosok-minden-evben/
milage = Milage(commute=13600, highway=3400)

# https://totalcar.hu/magazin/hirek/2023/05/24/hasznalt-elektromos-autok-vizsgalat-attekinthetobb-piac/
depreciation = {
    VehicleType.petrol: [
        Depreciation(year=3, value=66),
        Depreciation(year=5, value=46),
    ],
    VehicleType.diesel: [
        Depreciation(year=3, value=66),
        Depreciation(year=5, value=46),
    ],
    VehicleType.bev: [
        Depreciation(year=3, value=63),
        Depreciation(year=5, value=37),
    ],
}

consumption = {
    VehicleType.petrol: Consumption(average=6.0, highway=8.0),
    VehicleType.diesel: Consumption(average=5.0, highway=7.0),
    VehicleType.bev: Consumption(average=16.0, highway=21.0),
}

# https://penzugyi-tudakozo.hu/ennyibe-kerul-egy-auto-fenntartasa-2023-ban/
fees = {
    VehicleType.petrol: Fees(
        tax=30_000,
        service=120_000,
        insurance=55_000 + 150_000,
        parking=60_000,
        vignette=50_000,
    ),
    VehicleType.diesel: Fees(
        tax=30_000,
        service=120_000,
        insurance=55_000 + 150_000,
        parking=60_000,
        vignette=50_000,
    ),
    VehicleType.bev: Fees(
        tax=0,
        service=15_000,
        insurance=55_000 + 35_0000,
        parking=60_000,
        vignette=50_000,
    ),
}
