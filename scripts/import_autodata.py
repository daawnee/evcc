"""Convert scraped auto-data.net variants (JSON-Lines from the auto_data_net spider) into the evcc
car database: classify the powertrain, map fuel consumption into CarData, fill
depreciation/service/insurance/tax from the type-level fallbacks, and merge into data/cars/.

Consumption mapping (auto-data.net gives L/100km urban / extra-urban / combined):
  consumption.average (commute leg) <- urban   (city burns more for ICE)
  consumption.highway (travel leg)  <- extra-urban
  missing values fall back to the combined figure.

Pure-electric variants are skipped (BEVs already come from ev-database). No photos (auto-data.net
images aren't redistributed); the UI shows a placeholder.

Usage:
    python scripts/import_autodata.py ev_database_org/autodata_full.jl
    python scripts/import_autodata.py ev_database_org/autodata_full.jl --dry-run
"""

import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from models.calculate.input import (  # noqa: E402
    DEFAULT_ELECTRIC_CONSUMPTION,
    DEFAULT_INSURANCE,
    DEFAULT_SERVICE,
    DEFAULT_TAX,
    CarData,
    Consumption,
    FuelType,
    VehicleType,
)

DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "cars"))
HIGHWAY_FACTOR = 1.2  # phev electric highway leg vs city, when only one figure is known


def classify(fuel_type: str, powertrain: str):
    p = (powertrain or "").lower()
    ft = (fuel_type or "").lower()
    if "plug-in" in p or "phev" in p:
        return VehicleType.phev
    if "hev" in p or "hybrid" in p or "hybrid" in ft:
        return VehicleType.hybrid
    if "electric" in p or ft == "electricity":
        return None  # pure BEV — already covered by ev-database
    if "petrol" in ft or "gasoline" in ft:
        return VehicleType.petrol
    if "diesel" in ft:
        return VehicleType.diesel
    return None  # LPG / CNG / hydrogen / unknown


def combustion_fuel(fuel_type: str) -> FuelType:
    return FuelType.diesel if "diesel" in (fuel_type or "").lower() else FuelType.petrol


def kwh_100(value):
    if not value:
        return None
    m = re.search(r"([\d.]+)\s*kWh/100", value)
    return float(m.group(1)) if m else None


def slug(*parts: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", " ".join(p for p in parts if p).lower()).strip("-")
    return s or "car"


def model_id_for(row: dict) -> str:
    ad_id = urlparse(row["url"]).path.rstrip("/").rsplit("-", 1)[-1]
    base = slug(row.get("make", ""), row.get("model", ""), row.get("variant", ""))[:80]
    return f"{base}-{ad_id}".strip("-")


def to_car_data(row: dict, vt: VehicleType) -> CarData:
    urban = row.get("cons_urban")
    extra = row.get("cons_extra")
    combined = row.get("cons_combined")
    average = urban if urban is not None else combined
    highway = extra if extra is not None else combined

    electric = None
    fuel = None
    if vt in (VehicleType.hybrid, VehicleType.phev, VehicleType.petrol, VehicleType.diesel):
        fuel = combustion_fuel(row.get("fuel_type"))
    if vt == VehicleType.phev:
        ekwh = kwh_100(row.get("elec_consumption"))
        if ekwh:
            electric = Consumption(average=round(ekwh, 1), highway=round(ekwh * HIGHWAY_FACTOR, 1))
        else:
            electric = DEFAULT_ELECTRIC_CONSUMPTION[VehicleType.phev]

    def num(v):
        m = re.search(r"[\d.]+", v or "")
        return float(m.group(0)) if m else None

    return CarData(
        type=vt,
        make=row.get("make") or "",
        model=" ".join(p for p in (row.get("model"), row.get("variant")) if p),
        consumption=Consumption(average=round(average, 1), highway=round(highway, 1)),
        service_yearly=DEFAULT_SERVICE[vt],
        insurance_yearly=DEFAULT_INSURANCE[vt],
        tax_yearly=DEFAULT_TAX[vt],
        fuel=fuel if vt != VehicleType.bev else None,
        electric_consumption=electric,
        specs={
            "body": row.get("body"),
            "seats": int(num(row.get("seats"))) if num(row.get("seats")) else None,
            "drivetrain": None,
            "source": "auto-data.net",
            "source_url": row.get("url"),
        },
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default=DATA_DIR)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.input, encoding="utf-8") if l.strip()]
    os.makedirs(args.out, exist_ok=True)
    index_path = os.path.join(args.out, "index.json")
    existing = json.load(open(index_path, encoding="utf-8")) if os.path.exists(index_path) else []

    imported, seen, skipped = [], set(), 0
    from collections import Counter
    by_type = Counter()

    for row in rows:
        if not row.get("make") or not row.get("model"):
            skipped += 1
            continue
        vt = classify(row.get("fuel_type"), row.get("powertrain"))
        if vt is None:
            skipped += 1
            continue
        mid = model_id_for(row)
        if mid in seen:
            continue
        seen.add(mid)
        try:
            car = to_car_data(row, vt)
        except Exception as e:
            print(f"  skip {mid}: {e}", file=sys.stderr)
            skipped += 1
            continue
        by_type[vt.value] += 1
        if not args.dry_run:
            d = os.path.join(args.out, mid)
            os.makedirs(d, exist_ok=True)
            json.dump(car.model_dump(exclude_none=True), open(os.path.join(d, "metadata.json"), "w"),
                      indent=2, ensure_ascii=False)
        imported.append({"model_id": mid, "make": car.make, "model": car.model, "type": vt.value, "photo": None})

    print(f"parsed {len(rows)} rows -> {len(imported)} cars, {skipped} skipped")
    print("by powertrain:", dict(by_type))
    if args.dry_run:
        for e in imported[:10]:
            print(f"  [{e['type']}] {e['make']} {e['model']}")
        return 0

    merged = [e for e in existing if e.get("model_id") not in seen] + imported
    json.dump(merged, open(index_path, "w"), indent=2, ensure_ascii=False)
    print(f"index.json now has {len(merged)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
