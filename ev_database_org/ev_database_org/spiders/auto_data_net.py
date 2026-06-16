"""Scrapes ICE / hybrid / PHEV car specs from auto-data.net for the evcc TCO calculator.

Crawl path: /en/allbrands -> brand pages (mainstream allowlist) -> model pages -> generation
pages (kept only if produced in MIN_YEAR or later) -> variant detail pages. Each variant yields a
raw dict; scripts/import_autodata.py classifies the powertrain and maps it into the CarData schema.

Routed through Zyte API (transparent mode) so auto-data.net's rate limiting / bot checks don't
stall the crawl, exactly like the ev-database spider.
"""

import re

import scrapy

# Brand slugs (from /en/<slug>-brand-<id>) sold in the European / Hungarian market.
MAINSTREAM_BRANDS = {
    "volkswagen", "toyota", "bmw", "mercedes-benz", "audi", "skoda", "ford", "opel",
    "renault", "peugeot", "citroen", "hyundai", "kia", "nissan", "fiat", "seat", "volvo",
    "mazda", "honda", "dacia", "suzuki", "mitsubishi", "jeep", "mini", "cupra", "ds",
    "alfa-romeo", "land-rover", "jaguar", "lexus", "smart", "subaru", "porsche",
}
MIN_YEAR = 2015

_BRAND_RE = re.compile(r"^/en/([a-z0-9-]+)-brand-\d+$")
_MODEL_RE = re.compile(r"-model-\d+$")
_GEN_RE = re.compile(r"-generation-\d+$")
_VARIANT_RE = re.compile(r"^/en/[a-z0-9.\-]+-\d+$")


def _is_variant(href: str) -> bool:
    return bool(_VARIANT_RE.match(href)) and not re.search(r"-(model|generation|brand)-\d+$", href)


def _row_dict(response) -> dict:
    """Flatten the spec table into {label: value}. auto-data.net rows are <th/td> label + value."""
    out = {}
    for tr in response.css("table tr"):
        cells = [
            re.sub(r"\s+", " ", " ".join(c.css("::text").getall())).strip()
            for c in tr.css("th, td")
        ]
        cells = [c for c in cells if c]
        if len(cells) >= 2 and len(cells[0]) < 60 and cells[0] not in out:
            out[cells[0]] = cells[1]
    return out


def _l100(value):
    """First L/100km figure from e.g. '9.3 l/100 km 25.3 US mpg ...'."""
    if not value:
        return None
    m = re.search(r"([\d.]+)\s*l/100", value)
    return float(m.group(1)) if m else None


def _first_year(text):
    if not text:
        return None
    m = re.search(r"(19|20)\d{2}", text)
    return int(m.group(0)) if m else None


class AutoDataNet(scrapy.Spider):
    name = "auto_data_net"
    allowed_domains = ["auto-data.net"]
    start_urls = ["https://www.auto-data.net/en/allbrands"]

    custom_settings = {
        "ZYTE_API_TRANSPARENT_MODE": True,
        "CONCURRENT_REQUESTS": 16,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 16,
        "DOWNLOAD_DELAY": 0,
    }

    def parse(self, response):  # /en/allbrands
        for href in set(response.css("a::attr(href)").getall()):
            m = _BRAND_RE.match(href or "")
            if m and m.group(1) in MAINSTREAM_BRANDS:
                yield response.follow(href, self.parse_brand)

    def parse_brand(self, response):
        for href in set(response.css("a::attr(href)").getall()):
            if href and _MODEL_RE.search(href):
                yield response.follow(href, self.parse_model)

    def parse_model(self, response):
        for href in set(response.css("a::attr(href)").getall()):
            if href and _GEN_RE.search(href):
                yield response.follow(href, self.parse_generation)

    def parse_generation(self, response):
        # Recency gate: the H1 lists production years, e.g. "Geely Atlas /2016, 2017, .../ specs".
        h1 = response.css("h1::text").get() or ""
        years = [int(y) for y in re.findall(r"(?:19|20)\d{2}", h1)]
        if years and max(years) < MIN_YEAR:
            return
        for href in set(response.css("a::attr(href)").getall()):
            if href and _is_variant(href):
                yield response.follow(href, self.parse_variant)

    def parse_variant(self, response):
        d = _row_dict(response)
        # make / model from the breadcrumb (…>> Make >> Model >> Generation >> variant)
        make = (response.css('a[href*="-brand-"]::text').get() or "").strip()
        model = (response.css('a[href*="-model-"]::text').get() or "").strip()

        urban = _l100(d.get("Fuel consumption (economy) - urban"))
        extra = _l100(d.get("Fuel consumption (economy) - extra urban"))
        combined = _l100(d.get("Fuel consumption (economy) - combined"))
        if urban is None and extra is None and combined is None:
            return  # no usable consumption -> skip

        yield {
            "url": response.url,
            "make": make,
            "model": model,
            "variant": d.get("Modification (Engine)"),
            "fuel_type": d.get("Fuel Type"),
            "powertrain": d.get("Powertrain Architecture"),
            "cons_urban": urban,
            "cons_extra": extra,
            "cons_combined": combined,
            "elec_consumption": d.get("Electric energy consumption"),
            "co2": d.get("CO 2 emissions"),
            "body": d.get("Body type"),
            "seats": d.get("Seats"),
            "power": d.get("Power") or d.get("System power"),
            "engine_cc": d.get("Engine displacement"),
            "start_year": _first_year(d.get("Start of production")),
        }
