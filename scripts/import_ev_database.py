"""Convert scraped ev-database.org car items into the evcc car database.

Reads a JSON-Lines file produced by the `ev_database_org` Scrapy spider and, for each car:
  - maps it into a complete `CarData` record (consumption converted Wh/km -> kWh/100km),
    filling depreciation / service / insurance / tax from the BEV type-level fallbacks
    (ev-database does not provide those),
  - downloads the hero photo to data/cars/<model_id>/photo.jpg,
  - writes data/cars/<model_id>/metadata.json,
  - rebuilds data/cars/index.json.

Usage:
    uv run --project ev_database_org scrapy crawl ev_database_org -O cars.jl   # produce input
    python scripts/import_ev_database.py cars.jl                                # import
    python scripts/import_ev_database.py cars.jl --no-photos --limit 50         # quick dry-ish run
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from urllib.parse import urlparse

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from models.calculate.input import (  # noqa: E402
    DEFAULT_INSURANCE,
    DEFAULT_SERVICE,
    DEFAULT_TAX,
    CarData,
    VehicleType,
)

DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "cars"))
BEV = VehicleType.bev


def model_id_from_url(url: str) -> str:
    """Stable, unique model_id from the ev-database detail URL. The numeric id is included
    because different model-year/battery variants can share the same name slug, e.g.
    https://ev-database.org/car/3403/Tesla-Model-3-RWD -> '3403-tesla-model-3-rwd'."""
    parts = urlparse(url).path.rstrip("/").split("/")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", parts[-1]).strip("-").lower()
    car_id = parts[-2] if len(parts) >= 2 and parts[-2].isdigit() else ""
    return f"{car_id}-{slug}".strip("-") or "car"


def consumption_kwh_100km(wh_per_km):
    return round(wh_per_km / 10, 1) if wh_per_km is not None else None


def to_car_data(row: dict) -> CarData:
    avg = consumption_kwh_100km(row.get("consumption_real_combined_whkm"))
    hwy = consumption_kwh_100km(row.get("consumption_highway_whkm"))
    # Fall back to combined for highway (or vice versa) if one is missing.
    avg = avg if avg is not None else hwy
    hwy = hwy if hwy is not None else avg

    prices = {}
    if row.get("price_uk_gbp") is not None:
        prices["UK_GBP"] = row["price_uk_gbp"]
    if row.get("price_nl_eur") is not None:
        prices["NL_EUR"] = row["price_nl_eur"]
    if row.get("price_de_eur") is not None:
        prices["DE_EUR"] = row["price_de_eur"]

    return CarData(
        type=BEV,
        make=row.get("make") or "",
        model=row.get("model") or "",
        consumption={"average": avg, "highway": hwy},
        service_yearly=DEFAULT_SERVICE[BEV],
        insurance_yearly=DEFAULT_INSURANCE[BEV],
        tax_yearly=DEFAULT_TAX[BEV],
        photo=None,  # set after a successful photo download
        price_new=prices or None,
        specs={
            "battery_kwh": row.get("battery_useable_kwh"),
            "battery_nominal_kwh": row.get("battery_nominal_kwh"),
            "chemistry": row.get("battery_chemistry"),
            "range_real_km": row.get("range_real_km"),
            "range_wltp_km": row.get("range_wltp_km"),
            "ac_power_kw": row.get("ac_power_kw"),
            "dc_max_kw": row.get("dc_max_kw"),
            "dc_10_80_min": row.get("dc_charge_time_10_80_min"),
            "acceleration_0_100_s": row.get("acceleration_0_100_s"),
            "top_speed_kmh": row.get("top_speed_kmh"),
            "drivetrain": row.get("drivetrain"),
            "segment": row.get("segment"),
            "body": row.get("body"),
            "seats": row.get("seats"),
            "heat_pump": row.get("heat_pump"),
            "source": "ev-database.org",
            "source_url": row.get("url"),
        },
    )


def download_photo(url: str, dest: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "evcc-importer/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception as e:  # network/HTTP errors shouldn't abort the whole import
        print(f"    photo failed: {e}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="JSON-Lines file from the ev_database_org spider")
    ap.add_argument("--out", default=DATA_DIR, help="output data/cars directory")
    ap.add_argument("--no-photos", action="store_true", help="skip downloading hero photos")
    ap.add_argument("--limit", type=int, default=0, help="only import the first N cars")
    args = ap.parse_args()

    rows = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if args.limit:
        rows = rows[: args.limit]

    os.makedirs(args.out, exist_ok=True)

    # Preserve existing catalogue entries (e.g. ICE seed cars from other sources);
    # imported model_ids below will replace any same-id entries.
    index_path = os.path.join(args.out, "index.json")
    existing = []
    if os.path.exists(index_path):
        existing = json.load(open(index_path, encoding="utf-8"))

    imported_index, seen = [], set()
    written = 0

    for row in rows:
        if not row.get("url"):
            continue
        model_id = model_id_from_url(row["url"])
        if model_id in seen:
            continue
        seen.add(model_id)

        try:
            car = to_car_data(row)
        except Exception as e:
            print(f"  skip {model_id}: invalid ({e})", file=sys.stderr)
            continue

        car_dir = os.path.join(args.out, model_id)
        os.makedirs(car_dir, exist_ok=True)

        if not args.no_photos and row.get("hero_image_url"):
            if download_photo(row["hero_image_url"], os.path.join(car_dir, "photo.jpg")):
                car.photo = f"{model_id}/photo.jpg"

        with open(os.path.join(car_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(car.model_dump(exclude_none=True), f, indent=2, ensure_ascii=False)

        imported_index.append({
            "model_id": model_id,
            "make": car.make,
            "model": car.model,
            "type": car.type.value,
            "photo": car.photo,
        })
        written += 1
        print(f"  {model_id}: {car.make} {car.model}")

    # Merge: keep existing entries not re-imported, then add the imported ones.
    merged = [e for e in existing if e.get("model_id") not in seen] + imported_index
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"\nImported {written} cars to {args.out} (index.json has {len(merged)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
