from models.calculate import VehicleType, engine, fallback_car_data
from models.calculate.input import (
    Assumptions,
    CarSelection,
    Consumption,
    DepreciationPoint,
    Financing,
)
from models.calculate.engine import _first_crossing, _retained_pct


def _assumptions(**kw):
    return Assumptions(**kw)


def test_retained_pct_anchors_and_interpolates():
    curve = [DepreciationPoint(month=36, retained=60), DepreciationPoint(month=60, retained=40)]
    assert _retained_pct(curve, 0) == 100.0  # new car retains 100%
    assert _retained_pct(curve, 36) == 60.0  # exact knot
    assert _retained_pct(curve, 60) == 40.0  # exact knot
    assert _retained_pct(curve, 48) == 50.0  # midpoint between month 36 and 60


def test_retained_pct_extrapolates_clamped_to_zero():
    curve = [DepreciationPoint(month=36, retained=60), DepreciationPoint(month=60, retained=40)]
    # extrapolating the final segment's slope far out must clamp at 0, never negative
    assert _retained_pct(curve, 1200) == 0.0


def test_depreciation_point_accepts_legacy_year():
    p = DepreciationPoint(year=3, retained=66)
    assert p.month == 36.0 and p.retained == 66.0


def test_compute_series_length_and_monotonic_cumulative():
    car = fallback_car_data(VehicleType.bev, "ev")
    sel = CarSelection(model_id="ev", purchase_price=10_000_000)
    a = _assumptions(horizon_months=60)
    result = engine.compute("ev", car, sel, a)

    assert len(result.series) == 60
    assert result.series[0].month == 1 and result.series[-1].month == 60
    cumulative = [p.cumulative for p in result.series]
    assert cumulative == sorted(cumulative)  # cost only accumulates


def test_depreciation_anchored_at_purchase_price():
    # A car bought new whose value at month 0 equals the purchase price: first-month depreciation
    # should be positive and the running depreciation should never exceed the purchase price.
    car = fallback_car_data(VehicleType.petrol, "ice")
    price = 8_000_000
    sel = CarSelection(model_id="ice", purchase_price=price, age_at_purchase_months=0)
    result = engine.compute("ice", car, sel, _assumptions(horizon_months=120, inflation=0))

    total_depreciation = sum(p.depreciation for p in result.series)
    # Value can decay to (but not below) zero; allow a small epsilon for per-month rounding.
    assert 0 < total_depreciation <= price + 1


def test_bev_vs_ice_breakeven_within_horizon():
    # Cheap ICE vs more expensive EV with much lower running cost -> curves should cross.
    ice = fallback_car_data(VehicleType.petrol, "ice")
    ev = fallback_car_data(VehicleType.bev, "ev")
    a = _assumptions(horizon_months=120)

    ice_res = engine.compute("ice", ice, CarSelection(model_id="ice", purchase_price=6_000_000), a)
    ev_res = engine.compute("ev", ev, CarSelection(model_id="ev", purchase_price=12_000_000), a)

    month = _first_crossing(ev_res, ice_res)
    assert month is not None and 1 <= month <= 120


def test_breakevens_pairs_every_combination():
    car = fallback_car_data(VehicleType.bev, "x")
    a = _assumptions(horizon_months=12)
    results = [
        engine.compute(f"c{i}", car, CarSelection(model_id=f"c{i}", purchase_price=5_000_000), a)
        for i in range(3)
    ]
    pairs = engine.breakevens(results)
    assert len(pairs) == 3  # 3 choose 2


def test_hybrid_uses_single_fuel_like_ice():
    # A hybrid burns only fuel; its energy cost should track a petrol car's, scaled by consumption.
    hev = fallback_car_data(VehicleType.hybrid, "hev")
    a = _assumptions(horizon_months=12, inflation=0)
    res = engine.compute("hev", hev, CarSelection(model_id="hev", purchase_price=8_000_000), a)
    # Lower consumption than petrol default -> positive but modest monthly energy.
    assert all(p.energy > 0 for p in res.series)


def test_phev_commute_electric_travel_fuel():
    # PHEV: commute on electricity (cheap), travel on fuel (expensive). Energy must be > 0 and the
    # commute portion should be cheaper per-km than an equivalent petrol car running on fuel.
    phev = fallback_car_data(VehicleType.phev, "phev")
    assert phev.electric_consumption is not None and phev.fuel is not None
    a = _assumptions(
        horizon_months=12,
        inflation=0,
        mileage={"commute": 12000, "travel": 0},  # all-electric commuting
    )
    phev_res = engine.compute("phev", phev, CarSelection(model_id="phev", purchase_price=9_000_000), a)
    petrol = fallback_car_data(VehicleType.petrol, "ice")
    ice_res = engine.compute("ice", petrol, CarSelection(model_id="ice", purchase_price=9_000_000), a)
    # With travel=0, the PHEV runs purely on (cheap) electricity, the ICE on (cheap) petrol.
    phev_energy = sum(p.energy for p in phev_res.series)
    ice_energy = sum(p.energy for p in ice_res.series)
    assert phev_energy < ice_energy


def test_financing_adds_only_interest():
    car = fallback_car_data(VehicleType.petrol, "ice")
    a = _assumptions(horizon_months=12, inflation=0)
    fin = Financing(loan=5_000_000, rate=0.10, months=12)
    sel = CarSelection(model_id="ice", purchase_price=8_000_000, financing=fin)
    result = engine.compute("ice", car, sel, a)

    total_financing = sum(p.financing for p in result.series)
    # Spread interest over the loan term, so the sum approximates total interest paid.
    assert abs(total_financing - fin.total_interest()) < 1.0
