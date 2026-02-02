"""Web scraping strategies for different job listing websites."""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
from urllib.parse import quote

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from repositories import Job, JobRepository
from utils import contains_currency, convert_ukrainian_date

logger = logging.getLogger(__name__)


class Site(Enum):
    """Enumeration of supported job listing websites."""

    FIRST_JOB_DOU = "https://jobs.dou.ua/first-job"
    DOU = "https://jobs.dou.ua/vacancies/"
    WORK = "https://www.work.ua/jobs"
    DJINNI = "https://djinni.co/jobs"


class ScraperError(Exception):
    """Base exception for scraper operations."""

    pass


class ElementParseError(ScraperError):
    """Raised when a job element cannot be parsed."""

    pass


class JobScraper(ABC):
    """Abstract base class for job scrapers."""

    def __init__(
        self,
        driver: webdriver.Chrome,
        repository: JobRepository,
        category: str,
    ) -> None:
        """
        Initialize the job scraper.

        Args:
            driver: Selenium WebDriver instance
            repository: JobRepository for storing scraped jobs
            category: Job category to scrape

        Raises:
            ValueError: If category is empty or invalid
            TypeError: If driver or repository are of wrong type
        """
        if not category or not isinstance(category, str):
            raise ValueError("Category must be a non-empty string")
        if not isinstance(repository, JobRepository):
            raise TypeError("repository must be a JobRepository instance")

        self.driver = driver
        self.repository = repository
        self.category = category.strip()
        logger.info(f"Initialized {self.__class__.__name__} for category: {category}")

    def find_jobs(self) -> int:
        """
        Scrape jobs from the website.

        Returns:
            Number of jobs successfully inserted

        Raises:
            ScraperError: If scraping fails
        """
        inserted_count = 0
        try:
            self.driver.get(self._get_url())
            job_elements = self._get_job_elements()
            logger.info(f"Found {len(job_elements)} job elements")

            for idx, element in enumerate(job_elements):
                try:
                    job = self._parse_job_element(element)
                    if job:
                        try:
                            self.repository.insert(job)
                            inserted_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to insert job: {e}")
                except ElementParseError as e:
                    logger.warning(f"Error parsing job element {idx}: {e}")
                except NoSuchElementException as e:
                    logger.debug(f"Element not found in job {idx}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error parsing job element {idx}: {e}")

            logger.info(f"Successfully inserted {inserted_count}/{len(job_elements)} jobs")
            return inserted_count

        except Exception as e:
            logger.error(
                f"Error during scraping {self.__class__.__name__}: {e}",
                exc_info=True,
            )
            raise ScraperError(f"Scraping failed: {e}") from e

    def _safe_find_element(
        self,
        element: WebElement,
        by: str,
        value: str,
        default: str = "",
    ) -> str:
        """
        Safely find an element and extract its text.

        Args:
            element: Parent WebElement to search within
            by: Locator strategy (e.g., By.CLASS_NAME)
            value: Locator value
            default: Default value if element not found

        Returns:
            Element text or default value
        """
        try:
            found = element.find_element(by, value)
            return found.text.strip() if found.text else default
        except NoSuchElementException:
            return default
        except Exception as e:
            logger.debug(f"Error finding element {by}={value}: {e}")
            return default

    def _safe_find_attribute(
        self,
        element: WebElement,
        by: str,
        value: str,
        attribute: str,
        default: str = "",
    ) -> str:
        """
        Safely find an element and extract its attribute.

        Args:
            element: Parent WebElement to search within
            by: Locator strategy (e.g., By.CLASS_NAME)
            value: Locator value
            attribute: Attribute name to extract
            default: Default value if not found

        Returns:
            Attribute value or default value
        """
        try:
            found = element.find_element(by, value)
            attr_value = found.get_attribute(attribute)
            return attr_value.strip() if attr_value else default
        except NoSuchElementException:
            return default
        except Exception as e:
            logger.debug(f"Error finding attribute {attribute} for {by}={value}: {e}")
            return default

    @abstractmethod
    def _parse_job_element(self, element: WebElement) -> Optional[Job]:
        """
        Parse a job element into a Job object.

        Args:
            element: WebElement containing job information

        Returns:
            Job object or None if parsing fails

        Raises:
            ElementParseError: If critical information cannot be extracted
        """
        pass

    @abstractmethod
    def _get_url(self) -> str:
        """
        Generate the URL for scraping.

        Returns:
            Full URL to scrape
        """
        pass

    @abstractmethod
    def _get_job_elements(self) -> list[WebElement]:
        """
        Get all job element containers from the page.

        Returns:
            List of WebElement objects representing individual jobs
        """
        pass


class FirstDouJobScraper(JobScraper):
    """Scraper for first-job.dou.ua."""

    def _get_url(self) -> str:
        """Generate URL with category parameter."""
        return f"{Site.FIRST_JOB_DOU.value}/?category={self.category}"

    def _get_job_elements(self) -> list[WebElement]:
        """Get job elements by class name."""
        return self.driver.find_elements(By.CLASS_NAME, "l-vacancy")

    def _parse_job_element(self, element: WebElement) -> Job | None:
        """
        Parse a first-job.dou.ua job element.

        Returns:
            Job object or None if parsing fails
        """
        try:
            title = element.find_element(By.CLASS_NAME, "vt").text.strip()
            description = element.find_element(By.CLASS_NAME, "sh-info").text.strip()
            company = element.find_element(By.CLASS_NAME, "company").text.strip()

            location = self._safe_find_element(
                element, By.CLASS_NAME, "cities", default="Не зазначено"
            )

            salary = self._safe_find_element(
                element, By.CLASS_NAME, "salary", default="Не зазначено"
            )

            link = self._safe_find_attribute(element, By.TAG_NAME, "a", "href", default="")

            date_posted_text = self._safe_find_element(element, By.CLASS_NAME, "date", default="")
            date_posted = convert_ukrainian_date(date_posted_text) if date_posted_text else None

            if not title or not company or not link:
                raise ElementParseError("Missing required fields: title, company, or link")

            logger.info(f"Found job: {title} at {company} ({location})")

            return Job(
                title=title,
                description=description,
                company=company,
                link=link,
                salary=salary,
                location=location,
                date_posted=date_posted,
            )

        except ElementParseError:
            raise
        except Exception as e:
            logger.debug(f"Error parsing first-job element: {e}")
            return None


class DouJobsScraper(FirstDouJobScraper):
    """Scraper for jobs.dou.ua with experience filter."""

    def _get_url(self) -> str:
        """Generate URL with search and experience filter."""
        return f"{Site.DOU.value}?search={self.category}&exp=0-1"


class WorkUaScraper(JobScraper):
    """Scraper for work.ua."""

    def _get_url(self) -> str:
        """Generate URL with encoded category."""
        encoded_category = quote(self.category).replace("/", "")
        url = f"{Site.WORK.value}-remote-{encoded_category}"
        return url.replace("%20", "+")

    def _get_job_elements(self) -> list[WebElement]:
        """Get job elements by class name."""
        return self.driver.find_elements(By.CLASS_NAME, "job-link")

    def _parse_job_element(self, element: WebElement) -> Optional[Job]:
        """
        Parse a work.ua job element.

        Returns:
            Job object or None if parsing fails
        """
        try:
            title_element = element.find_element(By.TAG_NAME, "h2").find_element(By.TAG_NAME, "a")
            title = title_element.text.strip()
            link = title_element.get_attribute("href") or ""

            description = element.find_element(By.CSS_SELECTOR, "p.ellipsis").text.strip()

            # Extract salary
            salary_elements = element.find_elements(
                By.CSS_SELECTOR, "div.job-link > *:nth-child(2) span"
            )
            salary = self._extract_salary_or_company(salary_elements, filter_func=contains_currency)

            # Extract company
            company_elements = element.find_elements(By.CSS_SELECTOR, "span.strong-600")
            company = self._extract_salary_or_company(
                company_elements, filter_func=lambda text: not contains_currency(text)
            )

            # Extract location
            location_elements = element.find_elements(By.XPATH, "./div[3]/span[2]")
            location = location_elements[0].text.strip() if location_elements else "Дистанційно"

            # Extract date posted
            date_posted = None
            date_elements = element.find_elements(By.TAG_NAME, "time")
            if date_elements:
                date_posted = date_elements[0].get_attribute("datetime")
                if date_posted:
                    date_posted = date_posted.split(" ")[0]

            if not title or not company or not link:
                raise ElementParseError("Missing required fields: title, company, or link")

            logger.info(f"Found job: {title} at {company} ({location})")

            return Job(
                title=title,
                description=description,
                company=company,
                link=link,
                salary=salary,
                location=location,
                date_posted=date_posted or "Не зазначено",
            )

        except ElementParseError:
            raise
        except Exception as e:
            logger.debug(f"Error parsing work.ua element: {e}")
            return None

    def _extract_salary_or_company(
        self,
        elements: list[WebElement],
        filter_func=None,
    ) -> str:
        """
        Extract salary or company from a list of elements.

        Args:
            elements: List of WebElements to search through
            filter_func: Optional filter function to apply to text

        Returns:
            Found text or "Не зазначено"
        """
        for element in elements:
            text = element.text.strip()
            if text and (filter_func is None or filter_func(text)):
                return text
        return "Не зазначено"


class DjinniScraper(JobScraper):
    """Scraper for djinni.co."""

    def _get_url(self) -> str:
        """Generate URL with keyword and experience filters."""
        return f"{Site.DJINNI.value}?primary_keyword={self.category}&exp_level=no_exp&exp_level=1y"

    def _get_job_elements(self) -> list[WebElement]:
        """Get job elements by CSS selector."""
        return self.driver.find_elements(By.CSS_SELECTOR, 'li[id^="job-item-"]')

    def _parse_job_element(self, element: WebElement) -> Optional[Job]:
        """
        Parse a djinni.co job element.

        Returns:
            Job object or None if parsing fails
        """
        try:
            title_element = element.find_element(By.CLASS_NAME, "job-item__title-link")
            title = title_element.text.strip()
            link = title_element.get_attribute("href") or "Невідомо"

            company_element = element.find_element(
                By.CSS_SELECTOR, '[data-analytics="company_page"]'
            )
            company = company_element.text.strip()

            # Try to find original or truncated description
            description = self._safe_find_element(
                element, By.CLASS_NAME, "js-original-text", default=""
            )
            if not description:
                description = self._safe_find_element(
                    element, By.CLASS_NAME, "js-truncated-text", default=""
                )

            location = self._safe_find_element(
                element, By.CLASS_NAME, "text-nowrap", default="Не зазначено"
            )

            salary = self._safe_find_element(
                element,
                By.CLASS_NAME,
                "text-success text-nowrap",
                default="Не зазначено",
            )

            # Extract date posted with fallback
            date_posted = "Не зазначено"
            try:
                date_element = element.find_element(By.CSS_SELECTOR, '[data-toggle="tooltip"]')
                date_posted = (
                    date_element.get_attribute("data-original-title")
                    or date_element.text
                    or "Не зазначено"
                )
            except NoSuchElementException:
                pass

            if not title or not company or not link:
                raise ElementParseError("Missing required fields: title, company, or link")

            logger.info(f"Found job: {title} at {company} ({location})")

            return Job(
                title=title,
                description=description,
                company=company,
                link=link,
                location=location,
                salary=salary,
                date_posted=date_posted,
            )

        except ElementParseError:
            raise
        except Exception as e:
            logger.debug(f"Error parsing djinni element: {e}")
            return None
