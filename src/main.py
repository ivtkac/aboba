"""Command-line interface for the job scraper application."""

import logging
import sys
from dataclasses import dataclass
from enum import Enum

from builder import ChromeDriverConfig, JobScraperBuilder
from strategies import Site

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ExitCode(Enum):
    """Application exit codes."""

    SUCCESS = 0
    INVALID_ARGUMENTS = 1
    INVALID_SITE = 2
    EXECUTION_ERROR = 3
    KEYBOARD_INTERRUPT = 130


@dataclass
class Config:
    """Application configuration."""

    sites: list[str]
    categories: list[str]
    db_path: str = "jobs.db"
    headless: bool = True
    verbose: bool = False

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.sites:
            raise ValueError("At least one site must be specified")
        if not self.categories:
            raise ValueError("At least one category must be specified")


class SiteResolver:
    """Resolves site names to Site enums."""

    # Mapping of site names to Site enums
    _site_map = {
        "dou": Site.DOU,
        "work": Site.WORK,
        "first-job": Site.FIRST_JOB_DOU,
        "djinni": Site.DJINNI,
    }

    @classmethod
    def resolve(cls, site_name: str) -> Site | None:
        """
        Resolve a site name to its Site enum.

        Args:
            site_name: Name of the site

        Returns:
            Site enum or None if not found
        """
        return cls._site_map.get(site_name.lower())

    @classmethod
    def get_available_sites(cls) -> list[str]:
        """
        Get list of available site names.

        Returns:
            List of available site names
        """
        return list(cls._site_map.keys())


class JobScraperCLI:
    """Command-line interface for job scraper."""

    def __init__(self) -> None:
        """Initialize the CLI."""
        self.config: Config | None = None
        self.builder: JobScraperBuilder | None = None

    def run(self, args: list[str]) -> ExitCode:
        """
        Run the application with given arguments.

        Args:
            args: Command-line arguments

        Returns:
            ExitCode indicating success or failure
        """
        try:
            self.config = self._parse_arguments(args)
            self._validate_configuration()
            return self._execute_scraping()

        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            return ExitCode.KEYBOARD_INTERRUPT

        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            self._print_usage()
            return ExitCode.INVALID_ARGUMENTS

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return ExitCode.EXECUTION_ERROR

        finally:
            self._cleanup()

    def _parse_arguments(self, args: list[str]) -> Config:
        """
        Parse command-line arguments.

        Args:
            args: Command-line arguments

        Returns:
            Config object with parsed arguments

        Raises:
            ValueError: If arguments are invalid
        """
        if not args or "--help" in args or "-h" in args:
            self._print_usage()
            sys.exit(ExitCode.SUCCESS.value)

        config_dict = {
            "sites": [],
            "categories": [],
        }

        i = 0
        while i < len(args):
            arg = args[i]

            if arg == "--site":
                i += 1
                while i < len(args) and not args[i].startswith("--"):
                    config_dict["sites"].append(args[i])
                    i += 1
                i -= 1  # Adjust because the outer loop will increment

            elif arg == "--category":
                i += 1
                while i < len(args) and not args[i].startswith("--"):
                    config_dict["categories"].append(args[i])
                    i += 1
                i -= 1  # Adjust because the outer loop will increment

            elif arg == "--db":
                i += 1
                if i >= len(args):
                    raise ValueError("--db requires a path argument")
                config_dict["db_path"] = args[i]

            elif arg == "--verbose" or arg == "-v":
                config_dict["verbose"] = True

            elif arg == "--no-headless":
                config_dict["headless"] = False

            elif arg.startswith("--"):
                raise ValueError(f"Unknown argument: {arg}")

            i += 1

        if not config_dict["sites"]:
            raise ValueError("--site argument is required")
        if not config_dict["categories"]:
            raise ValueError("--category argument is required")

        return Config(**config_dict)

    def _validate_configuration(self) -> None:
        """
        Validate the configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.config is None:
            raise ValueError("Configuration not set")

        if self.config.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Verbose logging enabled")

        # Validate sites
        invalid_sites = []
        for site_name in self.config.sites:
            if SiteResolver.resolve(site_name) is None:
                invalid_sites.append(site_name)

        if invalid_sites:
            available = ", ".join(SiteResolver.get_available_sites())
            raise ValueError(
                f"Invalid sites: {', '.join(invalid_sites)}. Available sites: {available}"
            )

        logger.info("Configuration validated successfully")
        logger.info(f"Sites: {', '.join(self.config.sites)}")
        logger.info(f"Categories: {', '.join(self.config.categories)}")

    def _execute_scraping(self) -> ExitCode:
        """
        Execute the scraping process.

        Returns:
            ExitCode indicating success or failure

        Raises:
            Exception: If scraping fails
        """
        if self.config is None:
            raise ValueError("Configuration not set")

        try:
            # Create driver configuration
            driver_config = ChromeDriverConfig(headless=self.config.headless)

            # Create builder
            self.builder = JobScraperBuilder(
                db_path=self.config.db_path,
                driver_config=driver_config,
            )

            # Add scrapers
            for site_name in self.config.sites:
                site = SiteResolver.resolve(site_name)
                if site is None:
                    logger.warning(f"Skipping unsupported site: {site_name}")
                    continue

                for category in self.config.categories:
                    self.builder.add_scraper(site, category)

            # Execute scraping
            logger.info("Starting job scraping...")
            total_jobs = self.builder.execute()

            logger.info("Job scraping completed successfully!")
            logger.info(f"Total jobs inserted: {total_jobs}")

            return ExitCode.SUCCESS

        except Exception as e:
            logger.error(f"Scraping execution failed: {e}", exc_info=True)
            return ExitCode.EXECUTION_ERROR

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self.builder:
            try:
                self.builder.close()
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")

    @staticmethod
    def _print_usage() -> None:
        """Print usage information."""
        available_sites = ", ".join(SiteResolver.get_available_sites())
        print(
            f"""
Job Scraper - Web scraper for job listings

Usage:
    python -m main [OPTIONS]

Options:
    --site SITE [SITE ...]       Sites to scrape (required)
                                 Available: {available_sites}

    --category CATEGORY [...]    Job categories to search (required)

    --db PATH                    Path to SQLite database
                                 Default: jobs.db

    --verbose, -v                Enable verbose logging

    --no-headless                Run browser in non-headless mode

    --help, -h                   Show this help message

Examples:
    python -m main --site dou work --category "Python" ".NET"

    python -m main --site first-job --category "DevOps" --db custom.db

    python -m main --site djinni --category "JavaScript" --verbose

"""
        )


def main() -> int:
    """
    Main entry point for the application.

    Returns:
        Exit code
    """
    cli = JobScraperCLI()
    exit_code = cli.run(sys.argv[1:])
    return exit_code.value


if __name__ == "__main__":
    sys.exit(main())
