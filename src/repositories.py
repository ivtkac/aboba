from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass
class Job:
    title: str
    description: str
    company: str
    link: str
    location: str | None = None
    salary: str | None = None
    date_posted: str | None = None


@dataclass
class JobFilters:
    location: str | None = None
    company: str | None = None


class JobRepository:
    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = Path(db_path)
        self._setup_database()

    def insert(self, job: Job) -> bool:
        with self.get_db_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO jobs (title, description, company, salary, location, link, date_posted)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
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
                return True
            except Exception as _:
                conn.commit()
                return False

    def getall(self, filters: JobFilters | None = None) -> list[Job]:
        query = "SELECT title, description, link, company, location, salary, date_posted FROM jobs"
        params = []
        conditions = []

        if filters:
            if filters.location:
                conditions.append("location LIKE ?")
                params.append(f"%{filters.location}")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        with self.get_db_connection() as conn:
            cursor = conn.execute(query, params)
            return [Job(*row) for row in cursor.fetchall()]

        return []

    @contextmanager
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _setup_database(self):
        with self.get_db_connection() as conn:
            conn.execute("""
                        CREATE TABLE IF NOT EXISTS jobs(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL,
                            description TEXT,
                            company TEXT NOT NULL,
                            link TEXT UNIQUE NOT NULL,
                            location TEXT,
                            salary INTEGER,
                            date_posted TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(title, company, link)
                        )
                         """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_company ON jobs(company)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_location ON jobs(location)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_created_at ON jobs(created_at DESC)"
            )
