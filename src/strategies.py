from abc import ABC, abstractmethod
from enum import Enum
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium import webdriver

from repositories import Job, JobRepository


class Site(Enum):
    DOU = "https://jobs.dou.ua/first-job"
    WORK = "work.ua"


class JobScraper(ABC):
    def __init__(
        self, driver: webdriver.Chrome, repository: JobRepository, category: str
    ):
        self.driver = driver
        self.repository = JobRepository()
        self.category = category

    @abstractmethod
    def find_jobs(self):
        pass

    @abstractmethod
    def parse_job_elemet(self, element: WebElement) -> Job | None:
        pass


def get_url(site: Site, href: str) -> str:
    return f"{site}/{href}"


class DouJobScraper(JobScraper):
    def __init__(
        self, driver: webdriver.Chrome, repository: JobRepository, category: str
    ):
        self.url = get_url(Site.DOU, f"?category={category}")
        super().__init__(driver, repository, category)

    def find_jobs(self):
        try:
            self.driver.get(self.url)
            job_elements = self.driver.find_elements(By.CLASS_NAME, "l-vacancy")
            for element in job_elements:
                job = self.parse_job_elemet(element)
                if job:
                    self.repository.insert(job)
        finally:
            pass

    def parse_job_elemet(self, element: WebElement) -> Job | None:
        try:
            title = element.find_element(By.CLASS_NAME, "vt").text
            description = element.find_element(By.CLASS_NAME, "sh-info").text
            company = element.find_element(By.CLASS_NAME, "company").text.strip()
            location_elements = element.find_elements(By.CLASS_NAME, "cities")
            location = location_elements[0].text.strip() if location_elements else None
            salary = (
                element.find_element(By.CLASS_NAME, "salary").text.strip()
                if element.find_elements(By.CLASS_NAME, "salary")
                else None
            )
            link = element.find_element(By.TAG_NAME, "a").get_attribute("href") or ""
            date_posted = element.find_element(By.CLASS_NAME, "date").text

            return Job(
                title=title,
                description=description,
                company=company,
                link=link,
                salary=salary or "Не зазначено",
                location=location or "Не зазначено",
                date_posted=date_posted,
            )
        except Exception as _:
            raise
