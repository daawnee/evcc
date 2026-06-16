import scrapy
from scrapy_poet import DummyResponse

from ev_database_org.pages.car import CarPage
from ev_database_org.pages.navigation import NavigationPage


class EvDatabaseOrg(scrapy.Spider):
    name = "ev_database_org"
    start_urls = ["https://ev-database.org/"]

    async def parse(self, response: DummyResponse, nav: NavigationPage):
        """The homepage lists every BEV (~1365). Follow each car link to extraction.

        Subcategories are intentionally NOT followed: they are country catalogues
        (/uk/, /nl/, /de/) and cheatsheets that re-list the same cars, which would
        duplicate the crawl. The homepage alone covers the full set.
        """
        nav_item = await nav.to_item()

        for link in nav_item.items or []:
            yield scrapy.Request(link["url"], callback=self.parse_item)

        if nav_item.next_page:
            yield scrapy.Request(nav_item.next_page, callback=self.parse)

    async def parse_item(self, response: DummyResponse, page: CarPage):
        yield await page.to_item()
