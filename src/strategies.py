from abc import ABC, abstractmethod
from enum import Enum
import urllib.parse
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
import urllib
import logging


from utils import convert_ukrainian_date, contains_currency
from repositories import Job, JobRepository

logger = logging.getLogger(__name__)


class Site(Enum):
    FIRST_JOB_DOU = "https://jobs.dou.ua/first-job"
    DOU = "https://jobs.dou.ua/vacancies/"
    WORK = "https://www.work.ua/jobs"


class JobScraper(ABC):
    def __init__(
        self, driver: webdriver.Chrome, repository: JobRepository, category: str
    ):
        self.driver = driver
        self.repository = repository
        self.category = category

    def find_jobs(self):
        try:
            self.driver.get(self._get_url())
            job_elements = self._get_job_elements()

            for element in job_elements:
                try:
                    job = self._parse_job_element(element)
                    if job:
                        self.repository.insert(job)
                except NoSuchElementException as e:
                    logger.warning(f"Element not found for job: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing job: {e}", exc_info=True)

    def _safe_find_elemet(
        self, element: WebElement, by: str, value: str, default: str = ""
    ) -> str:
        try:
            return element.find_element(by, value).text.strip()
        except NoSuchElementException:
            return default

    def _safe_find_attribute(
        self,
        element: WebElement,
        by: str,
        value: str,
        attribute: str,
        default: str = "",
    ) -> str:
        try:
            el = element.find_element(by, value)
            return el.get_attribute(attribute) or default
        except NoSuchElementException:
            return default

    @abstractmethod
    def _parse_job_element(self, element: WebElement) -> Job | None:
        pass

    @abstractmethod
    def _get_url(self) -> str:
        pass

    @abstractmethod
    def _get_job_elements(self) -> list[WebElement]:
        pass


class FirstDouJobScraper(JobScraper):
    def _get_url(self) -> str:
        return f"{Site.FIRST_JOB_DOU.value}/?category={self.category}"

    def _get_job_elements(self) -> list[WebElement]:
        return self.driver.find_elements(By.CLASS_NAME, "l-vacancy")

    def _parse_job_element(self, element: WebElement) -> Job | None:
        title = element.find_element(By.CLASS_NAME, "vt").text
        description = element.find_element(By.CLASS_NAME, "sh-info").text
        company = element.find_element(By.CLASS_NAME, "company").text.strip()

        location_elements = element.find_elements(By.CLASS_NAME, "cities")
        location = location_elements[0].text.strip() if location_elements else None

        salary = (
            element.find_element(By.CLASS_NAME, "salary").text.strip()
            if element.find_elements(By.CLASS_NAME, "salary")
            else "Не зазначено"
        )
        link = element.find_element(By.TAG_NAME, "a").get_attribute("href") or ""
        date_posted = None
        date_posted = element.find_element(By.CLASS_NAME, "date").text
        date_posted = convert_ukrainian_date(date_posted) if date_posted else None

        return Job(
            title=title,
            description=description,
            company=company,
            link=link,
            salary=salary,
            location=location,
            date_posted=date_posted,
        )


class DouJobsScraper(FirstDouJobScraper):
    def _get_url(self) -> str:
        return f"{Site.DOU.value}/?search={self.category}&exp=0-1"


class WorkUaScraper(JobScraper):
    def _get_url(self) -> str:
        encoded_category = urllib.parse.quote(self.category).replace("/", "")
        url = f"{Site.WORK.value}-remote-{encoded_category}"
        return url.replace("%20", "+")

    def _get_job_elements(self) -> list[WebElement]:
        return self.driver.find_elements(By.CLASS_NAME, "job-link")

    def _parse_job_element(self, element: WebElement) -> Job | None:
        title_element = element.find_element(By.TAG_NAME, "h2").find_element(
            By.TAG_NAME, "a"
        )
        title = title_element.text
        link = title_element.get_attribute("href") or ""
        description = element.find_element(By.CSS_SELECTOR, "p.ellipsis").text

        salary_elements_full = element.find_elements(
            By.CSS_SELECTOR, "div.job-link > *:nth-child(2) span"
        )
        salary = self._extract_salary_or_company(
            salary_elements_full, filter_func=contains_currency
        )

        company_elements = element.find_elements(By.CSS_SELECTOR, "span.strong-600")
        company = self._extract_salary_or_company(
            company_elements, filter_func=lambda text: not contains_currency(text)
        )

        location_elements = element.find_elements(By.XPATH, "./div[3]/span[2]")
        location = (
            location_elements[0].text.strip() if location_elements else "Дистанційно"
        )

        date_posted = None
        date_elements = element.find_elements(By.TAG_NAME, "time")
        if date_elements:
            date_posted = date_elements[0].get_attribute("datetime")
            if date_posted:
                date_posted = date_posted.split(" ")[0]

        return Job(
            title=title,
            description=description,
            company=company,
            link=link,
            salary=salary,
            location=location,
            date_posted=date_posted or "Не зазначено",
        )

    def _extract_salary_or_company(self, elements: list[WebElement], filter_func=None):
        for el in elements:
            text = el.text.strip()
            if text and (filter_func is None or filter_func(text)):
                return text
        return "Не зазначено"
