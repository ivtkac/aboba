from abc import ABC, abstractmethod
from enum import Enum
import urllib.parse
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium import webdriver
import urllib
import datetime

from repositories import Job, JobRepository


class Site(Enum):
    DOU = "https://jobs.dou.ua/first-job"
    WORK = "https://www.work.ua/jobs"


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


def convert_ukrainian_date(date_str: str) -> str | None:
    current_year = datetime.datetime.now().year

    month_mapping = {
        "січня": 1,
        "лютого": 2,
        "березня": 3,
        "квітня": 4,
        "травня": 5,
        "червня": 6,
        "липня": 7,
        "серпня": 8,
        "вересня": 9,
        "жовтня": 10,
        "листопада": 11,
        "грудня": 12,
    }

    parts = date_str.strip()
    if len(parts) != 2:
        return None

    day = int(parts[0])
    month_name = parts[1].lower()
    month = month_mapping.get(month_name)

    if month is None:
        return None

    date_obj = datetime.date(current_year, month, day)
    return date_obj.strftime("%Y-%m-%d")


class DouJobScraper(JobScraper):
    def __init__(
        self, driver: webdriver.Chrome, repository: JobRepository, category: str
    ):
        self.url = f"{Site.DOU.value}/?category={category}"
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
            date_posted = None
            date_posted = element.find_element(By.CLASS_NAME, "date").text
            date_posted = convert_ukrainian_date(date_posted) if date_posted else None

            return Job(
                title=title,
                description=description,
                company=company,
                link=link,
                salary=salary or "Не зазначено",
                location=location or "Не зазначено",
                date_posted=date_posted or "Не зазначено",
            )
        except Exception as _:
            raise


class WorkUaScraper(JobScraper):
    def __init__(
        self, driver: webdriver.Chrome, repository: JobRepository, category: str
    ):
        encoded_category = urllib.parse.quote(category).replace("/", "")
        self.url = f"{Site.WORK.value}-remote-{encoded_category}/"
        self.url = self.url.replace("%20", "+")

        super().__init__(driver, repository, category)

    def find_jobs(self):
        try:
            self.driver.get(self.url)
            job_elements = self.driver.find_elements(By.CLASS_NAME, "job-link")
            for element in job_elements:
                job = self.parse_job_elemet(element)
                if job:
                    self.repository.insert(job)
        finally:
            pass

    def parse_job_elemet(self, element: WebElement) -> Job | None:
        try:
            title_element = element.find_element(By.TAG_NAME, "h2").find_element(
                By.TAG_NAME, "a"
            )
            title = title_element.text

            link = element.find_element(By.TAG_NAME, "a").get_attribute("href") or ""
            description = element.find_element(By.CSS_SELECTOR, "p.ellipsis").text

            salary_text = None
            salary_elements_full = element.find_elements(
                By.CSS_SELECTOR, "div.job-link > *:nth-child(2) span"
            )
            salary = None
            for el in salary_elements_full:
                text = el.text.strip()
                if "грн" in text or "₴" in text:
                    salary = text
                    break

            company = None
            company_elements = element.find_elements(By.CSS_SELECTOR, "span.strong-600")
            for el in company_elements:
                text = el.text.strip()
                if "грн" not in text and "₴" not in text and text:
                    company = text
                    break
            company = company or "Не вказано"

            location_elements = element.find_elements(By.XPATH, "./div[3]/span[2]")
            location = (
                location_elements[0].text.strip()
                if location_elements
                else "Дистанційно"
            )

            date_elements = element.find_elements(By.TAG_NAME, "time")
            date_posted = None
            if date_elements:
                date_posted = date_elements[0].get_attribute("datetime")
                if date_posted:
                    date_posted = date_posted.split(" ")[0]

            print(
                f"Found job: title={title}, description={description}, company={company}, link={link}, salary={salary}, location={location}, date_posted={date_posted}"
            )

            return Job(
                title=title,
                description=description,
                company=company,
                link=link,
                salary=salary or "Не зазначено",
                location=location,
                date_posted=date_posted or "Не зазначено",
            )
        except Exception as _:
            raise
