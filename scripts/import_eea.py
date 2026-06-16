"""Fetch petrol/diesel/hybrid/PHEV car data from the EEA CO2-monitoring dataset (Reg. EU 2019/631)
via the Discodata SQL REST API, aggregate per model, and import into the evcc car database.

EEA gives no service/insurance/depreciation/price and no photos — those are filled from the
type-level fallbacks in models.calculate.input (same approach as the BEV import for its gaps).

The Discodata service is intermittently flaky ("Service currently offline"); every query retries
with backoff. Column names and the country-filter column are discovered at runtime (the public
schema has drifted across vintages), so this adapts instead of hard-coding guesses.

Usage:
    python scripts/import_eea.py --country HU --dry-run        # explore: print discovered schema + sample
    python scripts/import_eea.py --country HU                  # import into data/cars/
    python scripts/import_eea.py --country HU --year 2023      # pin a specific reporting year
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from models.calculate.input import (  # noqa: E402
    DEFAULT_CONSUMPTION,
    DEFAULT_ELECTRIC_CONSUMPTION,
    DEFAULT_INSURANCE,
    DEFAULT_SERVICE,
    DEFAULT_TAX,
    CarData,
    Consumption,
    FuelType,
    VehicleType,
)

ENDPOINT = "https://discodata.eea.europa.eu/sql"
TABLE = "[CO2Emission].[latest].[co2cars]"
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "cars"))

# CO2 (g/km, WLTP) -> fuel consumption (L/100km): grams CO2 per litre burned.
CO2_PER_LITRE = {FuelType.petrol: 2330.0, FuelType.diesel: 2640.0}
# Highway (travel) consumption is modeled as a multiple of the WLTP-combined figure.
HIGHWAY_FACTOR = 1.25


def query(sql: str, page: int = 0, n: int = 1000, retries: int = 8) -> list:
    """Run a SQL query against Discodata, paging one block; retry through transient outages."""
    params = urllib.parse.urlencode({"query": sql, "p": page, "nrOfHits": n})
    url = f"{ENDPOINT}?{params}"
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "evcc-eea-import/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            last = str(e)
            time.sleep(min(5 * (attempt + 1), 30))
            continue
        if isinstance(data, dict) and data.get("errors"):
            msg = str(data["errors"])
            if "offline" in msg.lower():
                last = msg
                time.sleep(min(5 * (attempt + 1), 30))
                continue
            raise RuntimeError(f"Discodata error: {msg}\nSQL: {sql}")
        rows = data.get("results", []) if isinstance(data, dict) else []
        if rows and isinstance(rows[0], dict) and "error" in rows[0]:
            last = str(rows[0])
            time.sleep(min(5 * (attempt + 1), 30))
            continue
        return rows
    raise RuntimeError(f"Discodata unavailable after {retries} attempts: {last}")


def discover_columns() -> dict:
    """Map logical fields to the dataset's actual column names (which vary across vintages)."""
    sample = query(f"SELECT TOP 1 * FROM {TABLE}", n=1)
    if not sample:
        raise RuntimeError("no rows returned for schema discovery")
    cols = list(sample[0].keys())

    def find(*preds):
        for c in cols:
            cl = c.lower()
            if any(p(cl) for p in preds):
                return c
        return None

    mapping = {
        "country": find(lambda c: c == "country", lambda c: c == "ms", lambda c: c == "country_short"),
        "make": find(lambda c: c == "mk"),
        "model": find(lambda c: c == "cn"),
        "fuel": find(lambda c: c == "ft"),
        "mode": find(lambda c: c == "fm"),
        "co2": find(lambda c: c.startswith("ewltp")),
        "fuelcons": find(lambda c: "fuel consumption" in c),
        "elec": find(lambda c: "wh/km" in c or c == "z"),
        "erange": find(lambda c: "electric range" in c),
        "regs": find(lambda c: c == "r"),
        "year": find(lambda c: c == "year"),
        "status": find(lambda c: c == "status"),
    }
    missing = [k for k in ("country", "make", "model", "fuel", "year", "status") if not mapping[k]]
    if missing:
        raise RuntimeError(f"could not locate columns {missing}; available: {cols}")
    return mapping


def latest_final_year(col: dict, country: str) -> int:
    sql = (
        f"SELECT [{col['year']}] AS y, [{col['status']}] AS s, COUNT(*) AS n FROM {TABLE} "
        f"WHERE [{col['country']}]='{country}' GROUP BY [{col['year']}],[{col['status']}] "
        f"ORDER BY [{col['year']}] DESC"
    )
    rows = query(sql, n=200)
    finals = sorted({int(r["y"]) for r in rows if str(r["s"]).upper().startswith("F") and r["y"]}, reverse=True)
    if not finals:
        # fall back to any year present
        anyy = sorted({int(r["y"]) for r in rows if r["y"]}, reverse=True)
        return anyy[0]
    return finals[0]


def classify(ft: str, fm: str) -> VehicleType | None:
    ft = (ft or "").strip().lower()
    fm = (fm or "").strip().upper()
    if ft == "petrol":
        return VehicleType.petrol
    if ft == "diesel":
        return VehicleType.diesel
    if "/electric" in ft or ft in ("petrol-electric", "diesel-electric"):
        return VehicleType.phev if fm == "P" else VehicleType.hybrid
    return None  # electric/lpg/ng/hydrogen/e85 etc. — skipped


def fetch_rows(col: dict, country: str, year: int) -> list:
    sel = ", ".join(
        f"[{col[k]}] AS {k}"
        for k in ("make", "model", "fuel", "mode", "co2", "fuelcons", "elec", "erange", "regs")
        if col.get(k)
    )
    where = f"[{col['country']}]='{country}' AND [{col['year']}]={year} AND [{col['status']}]='F'"
    out, page = [], 0
    while True:
        rows = query(f"SELECT {sel} FROM {TABLE} WHERE {where}", page=page, n=2000)
        if not rows:
            break
        out.extend(rows)
        if len(rows) < 2000:
            break
        page += 1
    return out


def _num(v):
    try:
        f = float(v)
        return f if f == f else None  # drop NaN
    except (TypeError, ValueError):
        return None


def aggregate(rows: list) -> dict:
    """Group by (make, model, powertrain); registration-weighted means of the numeric fields."""
    groups = {}
    for r in rows:
        vt = classify(r.get("fuel"), r.get("mode"))
        if vt is None:
            continue
        mk = (r.get("make") or "").strip()
        cn = (r.get("model") or "").strip()
        if not mk or not cn:
            continue
        key = (mk.title(), cn.title(), vt)
        g = groups.setdefault(key, {"w": 0.0, "co2": 0.0, "fc": 0.0, "fcw": 0.0,
                                    "el": 0.0, "elw": 0.0, "er": 0.0, "erw": 0.0,
                                    "fuel": FuelType.diesel if "diesel" in (r.get("fuel") or "") else FuelType.petrol})
        w = _num(r.get("regs")) or 1.0
        g["w"] += w
        co2 = _num(r.get("co2"))
        if co2:
            g["co2"] += co2 * w
        fc = _num(r.get("fuelcons"))
        if fc:
            g["fc"] += fc * w
            g["fcw"] += w
        el = _num(r.get("elec"))
        if el:
            g["el"] += el * w
            g["elw"] += w
        er = _num(r.get("erange"))
        if er:
            g["er"] += er * w
            g["erw"] += w
    return groups


def build_car(make: str, model: str, vt: VehicleType, g: dict) -> CarData:
    fuel = g["fuel"] if vt in (VehicleType.hybrid, VehicleType.phev, VehicleType.petrol, VehicleType.diesel) else None
    base_fuel = fuel or FuelType.petrol
    w = g["w"] or 1.0

    # Combustion consumption (L/100km): prefer reported, else derive from CO2.
    if g["fcw"]:
        combined_l = g["fc"] / g["fcw"]
    else:
        co2 = g["co2"] / w if w else 0.0
        combined_l = co2 / (CO2_PER_LITRE[base_fuel] / 100.0) if co2 else None

    if vt == VehicleType.phev:
        # Charge-sustaining fuel consumption isn't reliably given (CO2/fuelcons are charge-weighted),
        # so use the type default for the fuel leg; take the electric leg from measured z (Wh/km).
        fuel_cons = DEFAULT_CONSUMPTION[VehicleType.phev]
        consumption = Consumption(average=fuel_cons.average, highway=fuel_cons.highway)
        if g["elw"]:
            ekwh = (g["el"] / g["elw"]) / 10.0  # Wh/km -> kWh/100km
            electric = Consumption(average=round(ekwh, 1), highway=round(ekwh * 1.2, 1))
        else:
            electric = DEFAULT_ELECTRIC_CONSUMPTION[VehicleType.phev]
    else:
        if combined_l and combined_l > 1:
            consumption = Consumption(average=round(combined_l, 1), highway=round(combined_l * HIGHWAY_FACTOR, 1))
        else:
            consumption = DEFAULT_CONSUMPTION[vt]
        electric = None

    erange = round(g["er"] / g["erw"]) if g["erw"] else None
    return CarData(
        type=vt,
        make=make,
        model=model,
        consumption=consumption,
        service_yearly=DEFAULT_SERVICE[vt],
        insurance_yearly=DEFAULT_INSURANCE[vt],
        tax_yearly=DEFAULT_TAX[vt],
        fuel=fuel if vt != VehicleType.bev else None,
        electric_consumption=electric,
        specs={"range_wltp_km": erange, "source": "eea-co2cars"} if erange else {"source": "eea-co2cars"},
    )


def slug(*parts: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", "-".join(parts).lower()).strip("-")
    return s or "car"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", default="HU")
    ap.add_argument("--year", type=int, default=0)
    ap.add_argument("--out", default=DATA_DIR)
    ap.add_argument("--dry-run", action="store_true", help="print discovered schema + a few aggregated models, write nothing")
    ap.add_argument("--min-regs", type=float, default=0, help="skip models with fewer than N registrations")
    args = ap.parse_args()

    col = discover_columns()
    print("discovered columns:", {k: v for k, v in col.items() if v})
    year = args.year or latest_final_year(col, args.country)
    print(f"using country={args.country} year={year}")

    rows = fetch_rows(col, args.country, year)
    print(f"fetched {len(rows)} registration rows")
    groups = aggregate(rows)
    groups = {k: g for k, g in groups.items() if g["w"] >= args.min_regs}
    from collections import Counter
    print("powertrain models:", dict(Counter(vt.value for (_, _, vt) in groups)))

    if args.dry_run:
        for (mk, cn, vt), g in list(sorted(groups.items(), key=lambda kv: -kv[1]["w"]))[:12]:
            car = build_car(mk, cn, vt, g)
            print(f"  [{vt.value}] {mk} {cn}: cons={car.consumption.average}/{car.consumption.highway}"
                  f" elec={car.electric_consumption} fuel={car.fuel} regs={int(g['w'])}")
        return 0

    os.makedirs(args.out, exist_ok=True)
    index_path = os.path.join(args.out, "index.json")
    existing = json.load(open(index_path, encoding="utf-8")) if os.path.exists(index_path) else []

    imported, seen = [], set()
    for (mk, cn, vt), g in groups.items():
        model_id = slug(mk, cn, vt.value)
        if model_id in seen:
            continue
        seen.add(model_id)
        car = build_car(mk, cn, vt, g)
        d = os.path.join(args.out, model_id)
        os.makedirs(d, exist_ok=True)
        json.dump(car.model_dump(exclude_none=True), open(os.path.join(d, "metadata.json"), "w"),
                  indent=2, ensure_ascii=False)
        imported.append({"model_id": model_id, "make": car.make, "model": car.model, "type": vt.value, "photo": None})

    merged = [e for e in existing if e.get("model_id") not in seen] + imported
    json.dump(merged, open(index_path, "w"), indent=2, ensure_ascii=False)
    print(f"\nImported {len(imported)} ICE/hybrid models (index.json now {len(merged)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
