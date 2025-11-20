from builder import JobScraperBuilder
from strategies import Site


def main():
    builder = JobScraperBuilder()
    builder.add_scrapers(scrapers=[(Site.DOU, "DevOps"), (Site.DOU, "Support")])
    builder.add_scrapers(scrapers=[(Site.WORK, "DevOps"), (Site.WORK, "Support")])
    builder.add_scraper(Site.WORK, "Системний адміністратор")

    builder.execute()


if __name__ == "__main__":
    main()
