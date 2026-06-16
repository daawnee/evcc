"""Layered depreciation curves, resolved most-specific-first:

    per-model (CarData.depreciation in metadata)  ->  per-brand  ->  global per-type

Curves are lists of DepreciationPoint (retained % of new price at an age in MONTHS); the engine
adds the implicit month-0 = 100% anchor and interpolates between points at monthly resolution.

We currently only have credible *per-type* figures, so BRAND_DEPRECIATION is empty and per-model
curves have been removed from metadata.json. Populate the brand/model layers when real
per-brand / per-model depreciation data becomes available — the resolver picks them up automatically.
"""

from typing import List, Optional

from .input import DepreciationPoint, VehicleType

# Global per-type retained-value curves (% of new), by age in months.
# https://totalcar.hu/magazin/hirek/2023/05/24/hasznalt-elektromos-autok-vizsgalat-attekinthetobb-piac/
TYPE_DEPRECIATION = {
    VehicleType.petrol: [DepreciationPoint(month=36, retained=66), DepreciationPoint(month=60, retained=46)],
    VehicleType.diesel: [DepreciationPoint(month=36, retained=66), DepreciationPoint(month=60, retained=46)],
    VehicleType.bev: [DepreciationPoint(month=36, retained=63), DepreciationPoint(month=60, retained=37)],
    VehicleType.hybrid: [DepreciationPoint(month=36, retained=68), DepreciationPoint(month=60, retained=48)],
    VehicleType.phev: [DepreciationPoint(month=36, retained=60), DepreciationPoint(month=60, retained=40)],
}

# Per-brand overrides, keyed by lowercase make (optionally per type). Empty until real data exists.
BRAND_DEPRECIATION: dict = {}


def resolve_depreciation(
    vtype: VehicleType, make: str = "", model_curve: Optional[List[DepreciationPoint]] = None
) -> List[DepreciationPoint]:
    """Return the most specific available curve: per-model, else per-brand, else per-type."""
    if model_curve:
        return model_curve
    brand = BRAND_DEPRECIATION.get((make or "").strip().lower())
    if brand:
        return brand
    return TYPE_DEPRECIATION[vtype]
