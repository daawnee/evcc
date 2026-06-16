from pydantic import BaseModel, Field, model_validator
from enum import Enum
from typing import Dict, List, Optional


class VehicleType(str, Enum):
    bev = "bev"
    petrol = "petrol"
    diesel = "diesel"
    hybrid = "hybrid"  # self-charging (HEV) — burns fuel only
    phev = "phev"  # plug-in hybrid — electricity for commute, fuel for travel


class FuelType(str, Enum):
    petrol = "petrol"
    diesel = "diesel"


class Financing(BaseModel):
    loan: float
    rate: float  # annual interest rate, e.g. 0.08 for 8%
    months: int

    def monthly(self) -> float:
        if self.months <= 0:
            return 0.0
        if self.rate == 0:
            return self.loan / self.months
        r = self.rate / 12
        return r * (1 / (1 - (1 + r) ** (-self.months))) * self.loan

    def total(self) -> float:
        return self.monthly() * self.months

    def total_interest(self) -> float:
        return self.total() - self.loan


class Consumption(BaseModel):
    average: float  # per 100 km, used for commute (L for ICE, kWh for BEV)
    highway: float  # per 100 km, used for travel


class DepreciationPoint(BaseModel):
    """Retained value (% of the new price) at a given age in MONTHS. The engine interpolates
    between points at monthly resolution. A legacy {year, retained} point is accepted and
    converted to months for backward compatibility."""

    month: float
    retained: float

    @model_validator(mode="before")
    @classmethod
    def _accept_year(cls, data):
        if isinstance(data, dict) and "month" not in data and "year" in data:
            data = {**data, "month": float(data["year"]) * 12}
        return data


class Specs(BaseModel):
    """Descriptive spec sheet, not used by the TCO engine. Populated for BEVs from ev-database
    (and left empty for cars sourced elsewhere). Exists to power the comparison UI / browsing."""

    battery_kwh: Optional[float] = None  # usable capacity
    battery_nominal_kwh: Optional[float] = None
    chemistry: Optional[str] = None
    range_real_km: Optional[int] = None  # EVDB real range
    range_wltp_km: Optional[int] = None
    ac_power_kw: Optional[float] = None
    dc_max_kw: Optional[float] = None
    dc_10_80_min: Optional[int] = None
    acceleration_0_100_s: Optional[float] = None
    top_speed_kmh: Optional[int] = None
    drivetrain: Optional[str] = None
    segment: Optional[str] = None
    body: Optional[str] = None
    seats: Optional[int] = None
    heat_pump: Optional[bool] = None
    source: Optional[str] = None  # provenance, e.g. "ev-database.org"
    source_url: Optional[str] = None


class CarData(BaseModel):
    """Per-model data, sourced from the car database (Blob Storage) or a type fallback."""

    type: VehicleType
    make: str = ""
    model: str = ""
    consumption: Consumption  # L/100km for petrol/diesel/hybrid/phev; kWh/100km for bev
    # Optional per-model depreciation curve. When omitted, the engine resolves it from the
    # brand layer, then the global per-type curve (see models/calculate/depreciation.py).
    depreciation: Optional[List[DepreciationPoint]] = None
    service_yearly: float
    insurance_yearly: float
    tax_yearly: float = 0.0
    # Combustion fuel for hybrid/phev (the liquid side); ignored for bev/petrol/diesel.
    fuel: Optional[FuelType] = None
    # Electric-side consumption (kWh/100km) for phev; used for the commute (home-charged) leg.
    electric_consumption: Optional[Consumption] = None
    photo: Optional[str] = None
    # Additive, descriptive-only fields (ignored by the engine):
    price_new: Optional[Dict[str, float]] = None  # suggested new price by market, e.g. {"DE_EUR": 37970}
    specs: Optional[Specs] = None


class CarSelection(BaseModel):
    """A car the caller wants to evaluate. Everything except the three core fields is optional and,
    when omitted, resolved from the database (by ``model_id``) or from type-level defaults."""

    model_id: str
    purchase_price: float
    age_at_purchase_months: int = 0
    financing: Optional[Financing] = None

    # Optional overrides for database-sourced fields:
    type: Optional[VehicleType] = None
    consumption: Optional[Consumption] = None
    depreciation: Optional[List[DepreciationPoint]] = None
    service_yearly: Optional[float] = None
    insurance_yearly: Optional[float] = None
    tax_yearly: Optional[float] = None
    fuel: Optional[FuelType] = None
    electric_consumption: Optional[Consumption] = None


class EnergyPrices(BaseModel):
    electricity: float  # per kWh
    petrol: float  # per litre
    diesel: float  # per litre


class EnergyInflation(BaseModel):
    """Annual price-increase rate per energy carrier (e.g. 0.02 = +2%/yr), compounded monthly.
    Electricity typically rises slower than liquid fuels."""

    electricity: float = 0.015
    petrol: float = 0.045
    diesel: float = 0.045


class Mileage(BaseModel):
    commute: int  # km/year driven on the cheap energy tariff (home charging / local station)
    travel: int  # km/year driven on the expensive tariff (fast charging / highway)


class OtherYearly(BaseModel):
    parking: float
    vignette: float


class Assumptions(BaseModel):
    """User-adjustable assumptions shared across all compared cars. All fields are defaulted."""

    mileage: "Mileage" = Field(default_factory=lambda: DEFAULT_MILEAGE)
    energy_cheap: "EnergyPrices" = Field(default_factory=lambda: DEFAULT_ENERGY_CHEAP)
    energy_expensive: "EnergyPrices" = Field(default_factory=lambda: DEFAULT_ENERGY_EXPENSIVE)
    energy_inflation: EnergyInflation = Field(default_factory=EnergyInflation)
    other_yearly: "OtherYearly" = Field(default_factory=lambda: DEFAULT_OTHER_YEARLY)
    inflation: float = 0.05  # annual inflation applied to non-energy running costs
    horizon_months: int = 60  # default projection horizon: 5 years


class Root(BaseModel):
    cars: List[CarSelection]
    assumptions: Assumptions = Field(default_factory=Assumptions)

    @model_validator(mode="after")
    def _require_cars(self) -> "Root":
        if not self.cars:
            raise ValueError("at least one car is required")
        return self


### Defaults ###

# https://villanyautosok.hu/2021/04/18/ennyi-uzemanyagot-fustolnek-el-a-magyar-autosok-minden-evben/
DEFAULT_MILEAGE = Mileage(commute=13600, travel=3400)

# https://holtankoljak.hu/ — cheap = home charging / local station, expensive = fast charge / highway
DEFAULT_ENERGY_CHEAP = EnergyPrices(electricity=72.0, petrol=618.8, diesel=642.1)
DEFAULT_ENERGY_EXPENSIVE = EnergyPrices(electricity=225.0, petrol=708.9, diesel=722.9)

DEFAULT_OTHER_YEARLY = OtherYearly(parking=60_000, vignette=50_000)

# Consumption: L/100km for combustion types, kWh/100km for bev. For phev this is the combustion
# (charge-sustaining) consumption used on the travel leg; the commute leg uses DEFAULT_ELECTRIC_CONSUMPTION.
DEFAULT_CONSUMPTION = {
    VehicleType.petrol: Consumption(average=6.0, highway=8.0),
    VehicleType.diesel: Consumption(average=5.0, highway=7.0),
    VehicleType.bev: Consumption(average=16.0, highway=21.0),
    VehicleType.hybrid: Consumption(average=4.5, highway=6.0),
    VehicleType.phev: Consumption(average=6.0, highway=7.0),
}

# Electric-side consumption (kWh/100km) for phev's home-charged commute leg.
DEFAULT_ELECTRIC_CONSUMPTION = {
    VehicleType.phev: Consumption(average=20.0, highway=24.0),
}

# Depreciation curves live in models/calculate/depreciation.py (layered: type -> brand -> model).

# https://penzugyi-tudakozo.hu/ennyibe-kerul-egy-auto-fenntartasa-2023-ban/
DEFAULT_SERVICE = {
    VehicleType.petrol: 120_000.0,
    VehicleType.diesel: 120_000.0,
    VehicleType.bev: 15_000.0,
    VehicleType.hybrid: 100_000.0,
    VehicleType.phev: 95_000.0,
}

DEFAULT_INSURANCE = {
    VehicleType.petrol: 55_000.0 + 150_000.0,
    VehicleType.diesel: 55_000.0 + 150_000.0,
    VehicleType.bev: 55_000.0 + 35_000.0,
    VehicleType.hybrid: 55_000.0 + 150_000.0,
    VehicleType.phev: 55_000.0 + 120_000.0,
}

# In Hungary BEVs are tax-exempt; hybrids/PHEVs get reduced/zero rates.
DEFAULT_TAX = {
    VehicleType.petrol: 30_000.0,
    VehicleType.diesel: 30_000.0,
    VehicleType.bev: 0.0,
    VehicleType.hybrid: 15_000.0,
    VehicleType.phev: 0.0,
}


def fallback_car_data(vtype: VehicleType, model_id: str = "") -> CarData:
    """Build CarData from type-level defaults when a model isn't in the database."""
    fuel = FuelType.petrol if vtype in (VehicleType.hybrid, VehicleType.phev) else None
    return CarData(
        type=vtype,
        make=vtype.value,
        model=model_id or vtype.value,
        consumption=DEFAULT_CONSUMPTION[vtype],
        # depreciation left unset — resolved from the per-type curve at compute time.
        service_yearly=DEFAULT_SERVICE[vtype],
        insurance_yearly=DEFAULT_INSURANCE[vtype],
        tax_yearly=DEFAULT_TAX[vtype],
        fuel=fuel,
        electric_consumption=DEFAULT_ELECTRIC_CONSUMPTION.get(vtype),
    )


def apply_overrides(car: CarData, sel: CarSelection) -> CarData:
    """Return a copy of ``car`` with any fields explicitly set on the selection overriding it."""
    data = car.model_copy(deep=True)
    if sel.type is not None:
        data.type = sel.type
    if sel.consumption is not None:
        data.consumption = sel.consumption
    if sel.depreciation is not None:
        data.depreciation = sel.depreciation
    if sel.service_yearly is not None:
        data.service_yearly = sel.service_yearly
    if sel.insurance_yearly is not None:
        data.insurance_yearly = sel.insurance_yearly
    if sel.tax_yearly is not None:
        data.tax_yearly = sel.tax_yearly
    if sel.fuel is not None:
        data.fuel = sel.fuel
    if sel.electric_consumption is not None:
        data.electric_consumption = sel.electric_consumption
    return data
