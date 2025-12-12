from builder import JobScraperBuilder
from strategies import Site


def main():
    builder = JobScraperBuilder()
    builder.add_scrapers(
        scrapers=[(Site.FIRST_JOB_DOU, "DevOps"), (Site.DOU, "Junior .NET")]
    )
    builder.add_scrapers(scrapers=[(Site.WORK, "DevOps"), (Site.WORK, "Support")])
    builder.add_scraper(Site.WORK, "Системний адміністратор")
    builder.add_scraper(Site.DOU, "Trainee Python")

    builder.execute()


if __name__ == "__main__":
    main()
