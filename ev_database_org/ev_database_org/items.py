from dataclasses import dataclass


@dataclass
class Navigation:
    items: list | None = None
    next_page: str | None = None
    subcategories: list | None = None


@dataclass
class Car:
    url: str | None = None
    make: str | None = None
    model: str | None = None
    consumption_real_combined_whkm: int | None = None
    consumption_highway_whkm: int | None = None
    battery_useable_kwh: float | None = None
    battery_nominal_kwh: float | None = None
    battery_chemistry: str | None = None
    range_real_km: int | None = None
    range_wltp_km: int | None = None
    ac_power_kw: float | None = None
    dc_max_kw: float | None = None
    dc_charge_time_10_80_min: int | None = None
    acceleration_0_100_s: float | None = None
    top_speed_kmh: int | None = None
    drivetrain: str | None = None
    segment: str | None = None
    body: str | None = None
    seats: int | None = None
    heat_pump: bool | None = None
    price_uk_gbp: float | None = None
    price_nl_eur: float | None = None
    price_de_eur: float | None = None
    hero_image_url: str | None = None
