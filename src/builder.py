from repositories import JobRepository
from strategies import (
    DjinniScraper,
    JobScraper,
    DouJobsScraper,
    FirstDouJobScraper,
    Site,
    WorkUaScraper,
)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class JobScraperBuilder:
    def __init__(self) -> None:
        self.scrapers: list[JobScraper] = []
        self.driver = self._get_driver()
        self.repository = JobRepository()

    def add_scrapers(self, scrapers: list[tuple[Site, str]]):
        for site, category in scrapers:
            self.add_scraper(site, category)

    def add_scraper(self, site: Site, category: str):
        if not category or not category.strip():
            raise ValueError("Category cannot be empty")

        if not isinstance(site, Site):
            raise TypeError(f"Expected Site enum, got {type(site)}")

        scraper = self._create_scraper(site, category)
        if scraper:
            self.scrapers.append(scraper)

    def execute(self):
        for scraper in self.scrapers:
            scraper.find_jobs()

        self.driver.quit()

    def __enter__(self):
        self.driver = self._get_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()

    def _create_scraper(self, site: Site, category: str) -> JobScraper | None:
        if site == Site.FIRST_JOB_DOU:
            return FirstDouJobScraper(self.driver, self.repository, category)
        if site == Site.DOU:
            return DouJobsScraper(self.driver, self.repository, category)
        if site == Site.WORK:
            return WorkUaScraper(self.driver, self.repository, category)
        if site == Site.DJINNI:
            return DjinniScraper(self.driver, self.repository, category)
        return None

    def _get_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        return driver
