import re
from functools import cached_property

from ev_database_org.items import Car
from web_poet import Returns, WebPage, field, handle_urls


def _clean(text: str | None) -> str | None:
    """Collapse whitespace and strip; return None for empty/placeholder text."""
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    if not text or text.lower() in ("no data", "-", "n/a"):
        return None
    return text


def _to_int(text: str | None) -> int | None:
    """Extract the first integer found in the text."""
    if not text:
        return None
    m = re.search(r"-?\d+", text.replace(",", ""))
    return int(m.group()) if m else None


def _to_float(text: str | None) -> float | None:
    """Extract the first decimal number found in the text."""
    if not text:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return float(m.group()) if m else None


@handle_urls("ev-database.org")
class CarPage(WebPage, Returns[Car]):
    @field
    def url(self) -> str | None:
        return str(self.response.url)

    """Page object for an ev-database.org car detail page."""

    # ----- shared helpers -------------------------------------------------

    @cached_property
    def _h1_text(self) -> str | None:
        """Full, whitespace-collapsed text of the single detail-page H1
        (includes the nested generation <span>)."""
        parts = self.css("header.sub-header h1 ::text").getall()
        if not parts:
            parts = self.css("h1 ::text").getall()
        text = " ".join(p.strip() for p in parts if p.strip())
        return _clean(text)

    def _row_value(self, scope, label: str, exact: bool = True) -> str | None:
        """Within a Parsel selector `scope`, find the <td> whose first label
        cell matches `label` and return the next <td>'s text.

        With exact=True the label cell must equal `label` (after whitespace
        normalisation); with exact=False a prefix match is used (handles
        trailing '*' / whitespace in label cells)."""
        if scope is None:
            return None
        for td in scope.css("td"):
            cell = _clean(" ".join(td.css("::text").getall()))
            if cell is None:
                continue
            cell = cell.rstrip("*").strip()
            if (cell == label) if exact else cell.startswith(label):
                nxt = td.xpath("following-sibling::td[1]")
                if nxt:
                    return _clean(" ".join(nxt.css("::text").getall()))
        return None

    @cached_property
    def _battery(self):
        return self.css("#battery")

    @cached_property
    def _efficiency(self):
        return self.css("#efficiency")

    @cached_property
    def _charging(self):
        return self.css("#charging")

    @cached_property
    def _performance(self):
        return self.css("#performance")

    @cached_property
    def _misc(self):
        """The 'Miscellaneous' data-table (no id) located via its <h2>."""
        for table in self.css("div.data-table"):
            h2 = _clean(table.css("h2::text").get())
            if h2 == "Miscellaneous":
                return table
        return None

    @cached_property
    def _price_rows(self):
        """Return the <tr> rows of the 'Price' table (first inline-block of
        #pricing), each as (label_text, value_text)."""
        blocks = self.css("#pricing .inline-block")
        if not blocks:
            return []
        # The 'Price' inline-block is the one whose <h2> == 'Price'; fall back
        # to the first inline-block.
        price_block = None
        for block in blocks:
            if _clean(block.css("h2::text").get()) == "Price":
                price_block = block
                break
        if price_block is None:
            price_block = blocks[0]
        rows = []
        for tr in price_block.css("tr"):
            cells = tr.css("td")
            if len(cells) < 2:
                continue
            label = _clean(" ".join(cells[0].css("::text").getall()))
            value = _clean(" ".join(cells[1].css("::text").getall()))
            rows.append((label, value))
        return rows

    def _price_for(self, country: str) -> float | None:
        for label, value in self._price_rows:
            if label and country in label:
                # Only return a price when the value cell carries a number.
                if value and re.search(r"\d", value):
                    return _to_float(value)
                return None
        return None

    def _icon_value(self, anchor_href: str) -> str | None:
        """Text of the headline icon <p> for the given anchor href (e.g.
        '#efficiency'), taking the direct text before the inner <span>."""
        p = self.css(f"#icons a[href='{anchor_href}'] p")
        if not p:
            return None
        # text() (not ::text descendant) grabs the leading value, excluding the
        # trailing <span> label.
        direct = p.xpath("./text()").getall()
        return _clean(" ".join(direct)) or _clean(" ".join(p.css("::text").getall()))

    # ----- fields ---------------------------------------------------------

    @field
    def make(self) -> str | None:
        text = self._h1_text
        return text.split()[0] if text else None

    @field
    def model(self) -> str | None:
        text = self._h1_text
        if not text:
            return None
        parts = text.split(" ", 1)
        return parts[1] if len(parts) > 1 else None

    @field
    def consumption_real_combined_whkm(self) -> int | None:
        val = self._icon_value("#efficiency")
        if val is None:
            # First 'Vehicle Consumption' row within #efficiency (EVDB Real Range).
            val = self._row_value(self._efficiency, "Vehicle Consumption", exact=False)
        return _to_int(val)

    @field
    def consumption_highway_whkm(self) -> int | None:
        return _to_int(
            self._row_value(
                self.css("#real-consumption"), "Highway - Mild Weather", exact=False
            )
        )

    @field
    def battery_useable_kwh(self) -> float | None:
        return _to_float(self._row_value(self._battery, "Useable Capacity", exact=False))

    @field
    def battery_nominal_kwh(self) -> float | None:
        return _to_float(self._row_value(self._battery, "Nominal Capacity", exact=False))

    @field
    def battery_chemistry(self) -> str | None:
        btype = self._row_value(self._battery, "Battery Type")
        cathode = self._row_value(self._battery, "Cathode Material")
        if not btype:
            return None
        if cathode:
            return f"{btype} {cathode}"
        return btype

    @field
    def range_real_km(self) -> int | None:
        val = self._icon_value("#range")
        if val is None:
            # First 'Range' row within #efficiency (EVDB Real Range section).
            val = self._row_value(self._efficiency, "Range", exact=False)
        return _to_int(val)

    @field
    def range_wltp_km(self) -> int | None:
        """WLTP Range — the 'Range' row in the first 'WLTP Ratings' block."""
        if not self._efficiency:
            return None
        h3 = self._efficiency.xpath(
            ".//h3[starts-with(normalize-space(.), 'WLTP Ratings')]"
        )
        if not h3:
            return None
        block = h3[0].xpath("following-sibling::div[1]")
        return _to_int(self._row_value(block, "Range", exact=True))

    @field
    def ac_power_kw(self) -> float | None:
        return _to_float(self._row_value(self._charging, "Charge Power", exact=True))

    @field
    def dc_max_kw(self) -> float | None:
        return _to_float(
            self._row_value(self._charging, "Charge Power (max)", exact=True)
        )

    @field
    def dc_charge_time_10_80_min(self) -> int | None:
        """Fast-charging time in minutes. Among the 'Charge Time' cells in
        #charging, pick the one whose value is expressed in minutes (the
        Home/Destination one is in hours, e.g. '6h30m')."""
        if not self._charging:
            return None
        for td in self._charging.css("td"):
            label = _clean(" ".join(td.css("::text").getall()))
            if label and label.startswith("Charge Time"):
                nxt = td.xpath("following-sibling::td[1]")
                value = _clean(" ".join(nxt.css("::text").getall())) if nxt else None
                if value and re.search(r"^\d+\s*min", value):
                    return _to_int(value)
        return None

    @field
    def acceleration_0_100_s(self) -> float | None:
        return _to_float(
            self._row_value(self._performance, "Acceleration 0 - 100 km/h", exact=True)
        )

    @field
    def top_speed_kmh(self) -> int | None:
        return _to_int(self._row_value(self._performance, "Top Speed", exact=True))

    @field
    def drivetrain(self) -> str | None:
        return self._row_value(self._performance, "Drive", exact=True)

    @field
    def segment(self) -> str | None:
        return self._row_value(self._misc, "Segment", exact=True)

    @field
    def body(self) -> str | None:
        return self._row_value(self._misc, "Car Body", exact=True)

    @field
    def seats(self) -> int | None:
        return _to_int(self._row_value(self._misc, "Seats", exact=True))

    @field
    def heat_pump(self) -> bool | None:
        val = self._row_value(self._misc, "Heat pump (HP)", exact=True)
        if val is None:
            return None
        return val.strip().lower() == "yes"

    @field
    def price_uk_gbp(self) -> float | None:
        return self._price_for("United Kingdom")

    @field
    def price_nl_eur(self) -> float | None:
        return self._price_for("The Netherlands")

    @field
    def price_de_eur(self) -> float | None:
        return self._price_for("Germany")

    @field
    def hero_image_url(self) -> str | None:
        href = self.css("div.img-main .fotorama a::attr(href)").get()
        if href:
            return self.urljoin(href)
        # Fallback: og:image (strip the @2x variant to match the spec form).
        og = self.css("meta[property='og:image']::attr(content)").get()
        if og:
            return re.sub(r"@2x(\.\w+)$", r"\1", og)
        return None
