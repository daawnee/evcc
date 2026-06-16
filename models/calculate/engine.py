"""Pure TCO (total cost of ownership) math. No Azure or I/O dependencies, so it is directly
unit-testable. Given resolved car data plus shared assumptions, produces a monthly cost curve."""

from typing import List, Optional

from .depreciation import resolve_depreciation
from .input import Assumptions, CarData, CarSelection, DepreciationPoint, FuelType, VehicleType
from .output import Breakeven, CarResult, MonthlyPoint


def _retained_pct(curve: List[DepreciationPoint], age_months: float) -> float:
    """Retained value (% of new price) at the given age in months, by piecewise-linear
    interpolation over the curve. A new car (age 0) retains 100%. Beyond the last point,
    extrapolate along the final segment's slope, clamped to >= 0."""
    points = sorted({(0.0, 100.0)} | {(float(p.month), float(p.retained)) for p in curve})
    age = age_months

    if age <= points[0][0]:
        return points[0][1]

    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        if age <= x1:
            t = (age - x0) / (x1 - x0) if x1 != x0 else 0.0
            return y0 + t * (y1 - y0)

    x0, y0 = points[-2]
    x1, y1 = points[-1]
    slope = (y1 - y0) / (x1 - x0) if x1 != x0 else 0.0
    return max(0.0, y1 + slope * (age - x1))


def _fuel_price(fuel: FuelType, a: Assumptions) -> tuple:
    """(cheap, expensive) price per litre for a combustion fuel."""
    if fuel == FuelType.diesel:
        return a.energy_cheap.diesel, a.energy_expensive.diesel
    return a.energy_cheap.petrol, a.energy_expensive.petrol


def _fuel_inflation(fuel: FuelType, a: Assumptions) -> float:
    return a.energy_inflation.diesel if fuel == FuelType.diesel else a.energy_inflation.petrol


def _energy_components(car: CarData, a: Assumptions):
    """Nominal (pre-inflation) monthly energy cost split by carrier: (electricity, fuel, fuel_type).
    Each carrier inflates at its own rate, so they must be tracked separately.

    The commute leg uses the cheap tariff (home charging / local fuel), the travel leg the expensive
    tariff (fast charging / highway). For a PHEV the commute leg runs on grid electricity and the
    travel leg on the combustion fuel — so the commute/travel mileage split is the electric-vs-fuel
    driving share."""
    commute_km_m = a.mileage.commute / 12
    travel_km_m = a.mileage.travel / 12

    if car.type == VehicleType.bev:
        electricity = (
            commute_km_m / 100 * car.consumption.average * a.energy_cheap.electricity
            + travel_km_m / 100 * car.consumption.highway * a.energy_expensive.electricity
        )
        return electricity, 0.0, None

    if car.type == VehicleType.phev:
        fuel = car.fuel or FuelType.petrol
        elec = car.electric_consumption or car.consumption
        _, fuel_exp = _fuel_price(fuel, a)
        electricity = commute_km_m / 100 * elec.average * a.energy_cheap.electricity
        fuel_cost = travel_km_m / 100 * car.consumption.highway * fuel_exp
        return electricity, fuel_cost, fuel

    # petrol / diesel / hybrid: a single combustion fuel on both legs
    fuel = car.fuel or (FuelType.diesel if car.type == VehicleType.diesel else FuelType.petrol)
    cheap, exp = _fuel_price(fuel, a)
    fuel_cost = (
        commute_km_m / 100 * car.consumption.average * cheap
        + travel_km_m / 100 * car.consumption.highway * exp
    )
    return 0.0, fuel_cost, fuel


def compute(model_id: str, car: CarData, sel: CarSelection, a: Assumptions) -> CarResult:
    price = sel.purchase_price
    base_age = sel.age_at_purchase_months

    # Depreciation anchored at purchase: the entered price is the value at the purchase age, and the
    # curve's shape carries it forward from there. The curve is resolved per-model -> brand -> type.
    curve = resolve_depreciation(car.type, car.make, car.depreciation)
    anchor = _retained_pct(curve, base_age)

    def value(elapsed_months: int) -> float:
        retained = _retained_pct(curve, base_age + elapsed_months)
        return price * (retained / anchor) if anchor else price

    elec_nominal, fuel_nominal, fuel_type = _energy_components(car, a)
    elec_rate = a.energy_inflation.electricity
    fuel_rate = _fuel_inflation(fuel_type, a) if fuel_type else 0.0

    service_m = car.service_yearly / 12
    insurance_m = car.insurance_yearly / 12
    other_m = (car.tax_yearly + a.other_yearly.parking + a.other_yearly.vignette) / 12

    fin = sel.financing
    fin_months = fin.months if fin else 0
    fin_monthly = (fin.total_interest() / fin_months) if fin and fin_months else 0.0

    series: List[MonthlyPoint] = []
    cumulative = 0.0
    prev_value = value(0)  # equals the purchase price

    for m in range(1, a.horizon_months + 1):
        inflation_factor = (1 + a.inflation) ** (m / 12)

        cur_value = value(m)
        depreciation = prev_value - cur_value
        prev_value = cur_value

        # Energy uses per-carrier price inflation; other running costs use general inflation.
        energy = (
            elec_nominal * (1 + elec_rate) ** (m / 12)
            + fuel_nominal * (1 + fuel_rate) ** (m / 12)
        )
        service = service_m * inflation_factor
        insurance = insurance_m * inflation_factor
        other = other_m * inflation_factor
        financing = fin_monthly if m <= fin_months else 0.0

        total = depreciation + energy + service + insurance + other + financing
        cumulative += total

        series.append(
            MonthlyPoint(
                month=m,
                depreciation=round(depreciation, 2),
                energy=round(energy, 2),
                service=round(service, 2),
                insurance=round(insurance, 2),
                other=round(other, 2),
                financing=round(financing, 2),
                total=round(total, 2),
                cumulative=round(cumulative, 2),
            )
        )

    return CarResult(
        model_id=model_id,
        make=car.make,
        model=car.model,
        type=car.type,
        photo=car.photo,
        series=series,
    )


def _first_crossing(a: CarResult, b: CarResult) -> Optional[int]:
    n = min(len(a.series), len(b.series))
    prev_sign = 0
    for k in range(n):
        diff = a.series[k].cumulative - b.series[k].cumulative
        sign = (diff > 0) - (diff < 0)
        if sign == 0:
            return a.series[k].month
        if prev_sign != 0 and sign != prev_sign:
            return a.series[k].month
        prev_sign = sign
    return None


def breakevens(results: List[CarResult]) -> List[Breakeven]:
    """Pairwise first-crossing month between every pair of cars' cumulative cost curves."""
    out: List[Breakeven] = []
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            out.append(
                Breakeven(
                    car_a=results[i].model_id,
                    car_b=results[j].model_id,
                    month=_first_crossing(results[i], results[j]),
                )
            )
    return out
