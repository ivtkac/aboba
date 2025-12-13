from builder import JobScraperBuilder
from strategies import Site
import argparse


def main():
    parser = argparse.ArgumentParser(description="Job Scrapper")
    parser.add_argument(
        "--site",
        choices=["dou", "work", "first-job"],
        nargs="+",
        required=True,
        help="Sites to scrape",
    )
    parser.add_argument("--category", nargs="+", required=True, help="Job categories")

    args = parser.parse_args()

    sites_map = {"dou": Site.DOU, "work": Site.WORK, "first-job": Site.FIRST_JOB_DOU}

    builder = JobScraperBuilder()
    for site in args.site:
        for category in args.category:
            site_val = sites_map[site]
            builder.add_scraper(site_val, category)

    builder.execute()
    print("Finish scrapping")


if __name__ == "__main__":
    main()
