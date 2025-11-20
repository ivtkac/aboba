from repositories import Job
from strategies import JobScraper, DouJobScraper, Site, WorkUaScraper
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from repositories import JobRepository


class JobScraperBuilder:
    def __init__(self) -> None:
        self.scrapers: list[JobScraper] = []
        self.driver = self._get_driver()
        self.repository = JobRepository()
        self.jobs: list[Job] = []

    def add_scrapers(self, scrapers: list[tuple[Site, str]]):
        for site, category in scrapers:
            self.add_scraper(site, category)

    def add_scraper(self, site: Site, category: str):
        scraper = self._create_scraper(site, category)
        if scraper:
            self.scrapers.append(scraper)

    def execute(self):
        for scraper in self.scrapers:
            scraper.find_jobs()

        self.driver.quit()

    def get_jobs(self) -> list[Job]:
        return self.repository.getall()

    def _create_scraper(self, site: Site, category: str) -> JobScraper | None:
        if site == Site.DOU:
            return DouJobScraper(self.driver, self.repository, category)
        if site == Site.WORK:
            return WorkUaScraper(self.driver, self.repository, category)
        return None

    def _get_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        return driver
