from builder import JobScraperBuilder
from strategies import Site


def main():
    builder = JobScraperBuilder()
    builder.add_scrapers(scrapers=[(Site.DOU, "DevOps"), (Site.DOU, "Support")])
    builder.add_scrapers(scrapers=[(Site.WORK, "DevOps"), (Site.WORK, "Support")])
    builder.add_scraper(Site.WORK, "Системний адміністратор")

    builder.execute()

    jobs = builder.get_jobs()

    for job in jobs:
        print(f"{job.title} at {job.company} ({job.location}) - {job.link}")


if __name__ == "__main__":
    main()
