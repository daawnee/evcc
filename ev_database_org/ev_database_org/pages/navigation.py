import re
from urllib.parse import urlsplit

from ev_database_org.items import Navigation
from web_poet import Returns, WebPage, field, handle_urls

# Car detail links look like /car/{id}/{slug} (optionally country-prefixed,
# e.g. /uk/car/{id}/{slug}). Match defensively on the numeric id segment.
_CAR_HREF_RE = re.compile(r"/car/\d+/")


def _clean(text: str | None) -> str:
    """Collapse whitespace and strip. Returns empty string for falsy input."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


@handle_urls("ev-database.org")
class NavigationPage(WebPage, Returns[Navigation]):
    """Navigation page object for ev-database.org listing pages.

    Works across the layouts seen on the site:
    - the homepage / country overviews (``/``, ``/uk/``, ``/nl/``, ``/de/``)
      which render cars as ``div.list-item`` cards, and
    - the cheatsheet pages (``/cheatsheet/...``) which render cars as table rows.
    All cars are present in the raw HTML on a single page; pagination is purely
    client-side (jplist), so ``next_page`` is always null.
    """

    @field
    def items(self) -> list:
        """Links to car detail pages (``/car/{id}/{slug}``).

        On card layouts every car has two anchors per car (image + title) with
        the same href; the image anchor has no text while the title anchor
        carries the clean name in a trailing ``span.hidden``. Links are
        de-duplicated by absolute URL while preserving document order, and the
        best (non-empty) text seen for a URL is kept.
        """
        results: list[dict] = []
        index: dict[str, dict] = {}
        for anchor in self.css("a"):
            href = anchor.css("::attr(href)").get()
            if not href or not _CAR_HREF_RE.search(href):
                continue
            url = self.urljoin(href)
            # Clean full title lives in a trailing span.hidden on card layouts;
            # otherwise fall back to the anchor's own text (cheatsheet layout).
            text = _clean(anchor.css("span.hidden::text").get())
            if not text:
                text = _clean(" ".join(anchor.css("::text").getall()))
            existing = index.get(url)
            if existing is None:
                entry = {"url": url, "text": text}
                index[url] = entry
                results.append(entry)
            elif not existing["text"] and text:
                existing["text"] = text
        return results

    @field
    def next_page(self) -> str | None:
        """ev-database lists every car on one page, so there is no next page."""
        return None

    @field
    def subcategories(self) -> list:
        """Links to alternate listings / site sections.

        Combines the footer navigation (``div.footer-top-*`` — class is
        suffixed per country, e.g. ``footer-top-default`` or ``footer-top-uk``)
        with the country-catalogue switcher (``section.country-switcher``).
        Off-site links (e.g. sponsor banners) are skipped, and entries are
        de-duplicated by absolute URL, preserving order.
        """
        host = urlsplit(self.url).netloc
        results: list[dict] = []
        seen: set[str] = set()
        anchors = self.css('div[class^="footer-top-"] a') + self.css(
            "section.country-switcher a"
        )
        for anchor in anchors:
            href = anchor.css("::attr(href)").get()
            if not href:
                continue
            url = self.urljoin(href)
            # Keep only on-site links; drops external sponsor links that share
            # the footer container.
            if urlsplit(url).netloc != host:
                continue
            if url in seen:
                continue
            seen.add(url)
            text = _clean(" ".join(anchor.css("::text").getall()))
            results.append({"url": url, "text": text})
        return results
