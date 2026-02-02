"""Database repository for job storage and retrieval."""

import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Represents a job posting with details."""

    title: str
    description: str
    company: str
    link: str
    location: str | None = None
    salary: str | None = None
    date_posted: str | None = None

    def __post_init__(self) -> None:
        """Validate job fields after initialization."""
        if not self.title or not self.title.strip():
            raise ValueError("Job title cannot be empty")
        if not self.company or not self.company.strip():
            raise ValueError("Job company cannot be empty")
        if not self.link or not self.link.strip():
            raise ValueError("Job link cannot be empty")


@dataclass
class JobFilters:
    """Filters for querying jobs from the repository."""

    location: str | None = None
    company: str | None = None
    title: str | None = None

    def has_filters(self) -> bool:
        """Check if any filters are set."""
        return any([self.location, self.company, self.title])


class JobRepositoryError(Exception):
    """Base exception for job repository operations."""

    pass


class JobDuplicateError(JobRepositoryError):
    """Raised when attempting to insert a duplicate job."""

    pass


class JobRepository:
    """Repository for managing job postings in SQLite database."""

    def __init__(self, db_path: str = "jobs.db") -> None:
        """
        Initialize the job repository.

        Args:
            db_path: Path to the SQLite database file

        Raises:
            ValueError: If db_path is empty or invalid
        """
        if not db_path or not isinstance(db_path, str):
            raise ValueError("db_path must be a non-empty string")

        self.db_path = Path(db_path)
        self._setup_database()
        logger.info(f"JobRepository initialized with database at {self.db_path}")

    def insert(self, job: Job) -> bool:
        """
        Insert a job into the repository.

        Args:
            job: Job object to insert

        Returns:
            True if insertion was successful, False otherwise

        Raises:
            JobRepositoryError: If there's a database error
            ValueError: If job is invalid
        """
        if not isinstance(job, Job):
            raise ValueError("Expected Job instance")

        try:
            with self.get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        title, description, company, salary, location, link, date_posted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job.title,
                        job.description,
                        job.company,
                        job.salary,
                        job.location,
                        job.link,
                        job.date_posted,
                    ),
                )
                conn.commit()
                logger.debug(f"Successfully inserted job: {job.title}")
                return True
        except sqlite3.IntegrityError as e:
            logger.warning(f"Duplicate job detected: {job.link}")
            raise JobDuplicateError(f"Job with link {job.link} already exists") from e
        except sqlite3.Error as e:
            logger.error(f"Database error during insert: {e}")
            raise JobRepositoryError(f"Failed to insert job: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during insert: {e}")
            raise JobRepositoryError(f"Unexpected error during insert: {e}") from e

    def get_all(self, filters: JobFilters | None = None) -> list[Job]:
        """
        Retrieve all jobs from the repository with optional filters.

        Args:
            filters: Optional JobFilters for filtering results

        Returns:
            List of Job objects matching the criteria

        Raises:
            JobRepositoryError: If there's a database error
        """
        query = "SELECT title, description, link, company, location, salary, date_posted FROM jobs"
        params: list[str] = []
        conditions: list[str] = []

        if filters and filters.has_filters():
            if filters.location:
                conditions.append("location LIKE ?")
                params.append(f"%{filters.location}%")

            if filters.company:
                conditions.append("company LIKE ?")
                params.append(f"%{filters.company}%")

            if filters.title:
                conditions.append("title LIKE ?")
                params.append(f"%{filters.title}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute(query, params)
                jobs = [Job(*row) for row in cursor.fetchall()]
                logger.debug(f"Retrieved {len(jobs)} jobs with filters: {filters}")
                return jobs
        except sqlite3.Error as e:
            logger.error(f"Database error during retrieval: {e}")
            raise JobRepositoryError(f"Failed to retrieve jobs: {e}") from e
        except Exception as e:
            logger.error(f"Error while parsing jobs: {e}")
            raise JobRepositoryError(f"Error parsing job data: {e}") from e

    def get_by_link(self, link: str) -> Job | None:
        """
        Retrieve a job by its link.

        Args:
            link: Job link to search for

        Returns:
            Job object if found, None otherwise

        Raises:
            JobRepositoryError: If there's a database error
        """
        if not link or not isinstance(link, str):
            raise ValueError("Link must be a non-empty string")

        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT title, description, link, company, location, salary, date_posted
                    FROM jobs WHERE link = ?
                    """,
                    (link,),
                )
                row = cursor.fetchone()
                if row:
                    return Job(*row)
                return None
        except sqlite3.Error as e:
            logger.error(f"Database error during retrieval: {e}")
            raise JobRepositoryError(f"Failed to retrieve job: {e}") from e

    def delete_by_link(self, link: str) -> bool:
        """
        Delete a job by its link.

        Args:
            link: Job link to delete

        Returns:
            True if a job was deleted, False if no job with that link exists

        Raises:
            JobRepositoryError: If there's a database error
        """
        if not link or not isinstance(link, str):
            raise ValueError("Link must be a non-empty string")

        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute("DELETE FROM jobs WHERE link = ?", (link,))
                conn.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Deleted job with link: {link}")
                return deleted
        except sqlite3.Error as e:
            logger.error(f"Database error during deletion: {e}")
            raise JobRepositoryError(f"Failed to delete job: {e}") from e

    def count(self, filters: JobFilters | None = None) -> int:
        """
        Count jobs in the repository with optional filters.

        Args:
            filters: Optional JobFilters for counting

        Returns:
            Number of jobs matching criteria

        Raises:
            JobRepositoryError: If there's a database error
        """
        query = "SELECT COUNT(*) FROM jobs"
        params: list[str] = []
        conditions: list[str] = []

        if filters and filters.has_filters():
            if filters.location:
                conditions.append("location LIKE ?")
                params.append(f"%{filters.location}%")

            if filters.company:
                conditions.append("company LIKE ?")
                params.append(f"%{filters.company}%")

            if filters.title:
                conditions.append("title LIKE ?")
                params.append(f"%{filters.title}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute(query, params)
                count = cursor.fetchone()[0]
                return count
        except sqlite3.Error as e:
            logger.error(f"Database error during count: {e}")
            raise JobRepositoryError(f"Failed to count jobs: {e}") from e

    @contextmanager
    def get_db_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database connections.

        Yields:
            SQLite connection object

        Ensures:
            Connection is properly closed even if an error occurs
        """
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _setup_database(self) -> None:
        """Create database schema if it doesn't exist."""
        try:
            with self.get_db_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS jobs(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        company TEXT NOT NULL,
                        link TEXT UNIQUE NOT NULL,
                        location TEXT,
                        salary TEXT,
                        date_posted TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(title, company, link)
                    )
                    """
                )

                # Create indexes for better query performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_company ON jobs(company)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_location ON jobs(location)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON jobs(created_at DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_link ON jobs(link)")
                conn.commit()
                logger.info("Database schema initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to setup database: {e}")
            raise JobRepositoryError(f"Failed to setup database: {e}") from e
