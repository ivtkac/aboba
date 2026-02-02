"""Builder and factory classes for creating and managing job scrapers."""

import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from repositories import JobRepository
from strategies import (
    DjinniScraper,
    DouJobsScraper,
    FirstDouJobScraper,
    JobScraper,
    Site,
    WorkUaScraper,
)

logger = logging.getLogger(__name__)


class ScraperFactory:
    """Factory for creating scraper instances."""

    # Mapping of Site enum to scraper classes
    _scraper_map: dict[Site, type[JobScraper]] = {
        Site.FIRST_JOB_DOU: FirstDouJobScraper,
        Site.DOU: DouJobsScraper,
        Site.WORK: WorkUaScraper,
        Site.DJINNI: DjinniScraper,
    }

    @classmethod
    def create_scraper(
        cls,
        site: Site,
        category: str,
        driver: webdriver.Chrome,
        repository: JobRepository,
    ) -> JobScraper | None:
        """
        Create a scraper instance for the specified site.

        Args:
            site: Site enum indicating which website to scrape
            category: Job category to search for
            driver: Selenium WebDriver instance
            repository: JobRepository for storing jobs

        Returns:
            JobScraper instance or None if site is not supported

        Raises:
            ValueError: If category is empty or invalid
            TypeError: If site is not a Site enum
        """
        if not isinstance(site, Site):
            raise TypeError(f"Expected Site enum, got {type(site)}")

        scraper_class = cls._scraper_map.get(site)
        if scraper_class is None:
            logger.warning(f"No scraper available for site: {site}")
            return None

        try:
            scraper = scraper_class(driver, repository, category)
            logger.info(f"Created scraper: {scraper_class.__name__} for {site.name}")
            return scraper
        except ValueError as e:
            logger.error(f"Failed to create scraper: {e}")
            raise

    @classmethod
    def is_supported(cls, site: Site) -> bool:
        """
        Check if a site is supported.

        Args:
            site: Site enum to check

        Returns:
            True if site is supported, False otherwise
        """
        return site in cls._scraper_map

    @classmethod
    def supported_sites(cls) -> list[Site]:
        """
        Get list of all supported sites.

        Returns:
            List of supported Site enums
        """
        return list(cls._scraper_map.keys())


class ChromeDriverConfig:
    """Configuration for Chrome WebDriver."""

    def __init__(
        self,
        headless: bool = True,
        no_sandbox: bool = True,
        disable_dev_shm: bool = True,
        additional_args: list[str] | None = None,
    ) -> None:
        """
        Initialize Chrome driver configuration.

        Args:
            headless: Run Chrome in headless mode
            no_sandbox: Disable sandbox mode
            disable_dev_shm: Disable /dev/shm usage
            additional_args: Additional Chrome arguments
        """
        self.headless = headless
        self.no_sandbox = no_sandbox
        self.disable_dev_shm = disable_dev_shm
        self.additional_args = additional_args or []

    def apply_to_options(self, options: Options) -> Options:
        """
        Apply configuration to Chrome Options object.

        Args:
            options: Chrome Options instance

        Returns:
            Modified Chrome Options instance
        """
        if self.headless:
            options.add_argument("--headless")
        if self.no_sandbox:
            options.add_argument("--no-sandbox")
        if self.disable_dev_shm:
            options.add_argument("--disable-dev-shm-usage")

        for arg in self.additional_args:
            options.add_argument(arg)

        return options


class JobScraperBuilder:
    """Builder for configuring and executing job scrapers."""

    def __init__(
        self,
        db_path: str = "jobs.db",
        driver_config: ChromeDriverConfig | None = None,
    ) -> None:
        """
        Initialize the scraper builder.

        Args:
            db_path: Path to the SQLite database
            driver_config: ChromeDriverConfig instance for WebDriver configuration

        Raises:
            ValueError: If db_path is empty
        """
        if not db_path or not isinstance(db_path, str):
            raise ValueError("db_path must be a non-empty string")

        self.db_path = db_path
        self.driver_config = driver_config or ChromeDriverConfig()
        self.scrapers: list[JobScraper] = []
        self.driver: webdriver.Chrome | None = None
        self.repository: JobRepository | None = None
        self._is_closed = False

        logger.info(f"Initialized JobScraperBuilder with database: {db_path}")

    def add_scraper(self, site: Site, category: str) -> "JobScraperBuilder":
        """
        Add a scraper to the builder.

        Args:
            site: Site enum indicating which website to scrape
            category: Job category to search for

        Returns:
            Self for method chaining

        Raises:
            ValueError: If category is empty
            TypeError: If site is not a Site enum
            RuntimeError: If builder is already closed
        """
        if self._is_closed:
            raise RuntimeError("Cannot add scrapers to a closed builder")

        if not category or not isinstance(category, str):
            raise ValueError("Category must be a non-empty string")

        if not isinstance(site, Site):
            raise TypeError(f"Expected Site enum, got {type(site)}")

        # Initialize driver and repository if needed
        if self.driver is None:
            self.driver = self._create_driver()
        if self.repository is None:
            self.repository = JobRepository(self.db_path)

        # Create and add scraper
        scraper = ScraperFactory.create_scraper(site, category, self.driver, self.repository)

        if scraper:
            self.scrapers.append(scraper)
            logger.info(f"Added scraper for {site.name} with category: {category}")
        else:
            logger.warning(f"Failed to add scraper for {site.name}")

        return self

    def add_scrapers(self, scrapers: list[tuple[Site, str]]) -> "JobScraperBuilder":
        """
        Add multiple scrapers from a list of (site, category) tuples.

        Args:
            scrapers: List of (Site, category) tuples

        Returns:
            Self for method chaining

        Raises:
            TypeError: If scrapers is not a list
            ValueError: If any tuple is invalid
        """
        if not isinstance(scrapers, list):
            raise TypeError("scrapers must be a list")

        for site, category in scrapers:
            self.add_scraper(site, category)

        return self

    def execute(self) -> int:
        """
        Execute all scrapers and return total jobs inserted.

        Returns:
            Total number of jobs successfully inserted

        Raises:
            RuntimeError: If no scrapers have been added
            Exception: If scraping fails
        """
        if not self.scrapers:
            raise RuntimeError("No scrapers have been added")

        if self.driver is None:
            self.driver = self._create_driver()

        total_inserted = 0
        logger.info(f"Starting execution of {len(self.scrapers)} scrapers")

        for scraper in self.scrapers:
            try:
                inserted = scraper.find_jobs()
                total_inserted += inserted
            except Exception as e:
                logger.error(f"Error executing scraper: {e}", exc_info=True)

        logger.info(f"Execution complete. Total jobs inserted: {total_inserted}")
        return total_inserted

    def __enter__(self) -> "JobScraperBuilder":
        """
        Context manager entry.

        Returns:
            Self for use in with statement
        """
        if self.driver is None:
            self.driver = self._create_driver()
        if self.repository is None:
            self.repository = JobRepository(self.db_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Context manager exit with cleanup.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        self.close()

    def close(self) -> None:
        """
        Clean up resources.

        Closes the WebDriver and marks the builder as closed.
        """
        if self._is_closed:
            return

        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")

        self._is_closed = True
        logger.info("JobScraperBuilder closed")

    def _create_driver(self) -> webdriver.Chrome:
        """
        Create a Chrome WebDriver instance with configured options.

        Returns:
            Configured Chrome WebDriver instance

        Raises:
            Exception: If WebDriver creation fails
        """
        try:
            options = Options()
            self.driver_config.apply_to_options(options)
            driver = webdriver.Chrome(options=options)
            logger.info("Chrome WebDriver created successfully")
            return driver
        except Exception as e:
            logger.error(f"Failed to create Chrome WebDriver: {e}")
            raise

    def __repr__(self) -> str:
        """String representation of the builder."""
        return (
            f"JobScraperBuilder(db_path={self.db_path}, "
            f"scrapers={len(self.scrapers)}, closed={self._is_closed})"
        )
