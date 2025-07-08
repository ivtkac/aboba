import sqlite3
from dataclasses import dataclass
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


@dataclass
class Job:
    title: str
    description: str
    company: str
    link: str
    location: Optional[str] = None
    salary: Optional[str] = None
    date_posted: Optional[str] = None


class SkipJobException(Exception):
    """Custom exception to skip certain jobs based on criteria."""

    def __init__(self, message: str):
        super().__init__(message)


class JobScraper:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
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
                         UNIQUE(title, company, link))""")

    def get_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(options=options)

    def scrape_dou_jobs(
        self,
        category: str,
        skip_positions: List[str] | None = None,
        preffered_positions: List[str] | None = None,
    ) -> List[Job]:
        url = f"https://jobs.dou.ua/first-job/?category={category}"
        driver = self.get_driver()
        jobs = []

        try:
            driver.get(url)
            job_elements = driver.find_elements(By.CLASS_NAME, "l-vacancy")

            for element in job_elements:
                try:
                    job = self.parse_job_element(
                        element,
                        skip_positions or [],
                        preffered_positions or [],
                    )
                    if job:
                        jobs.append(job)
                except SkipJobException as e:
                    print(f"Skipping job: {e}")
                    continue
        except Exception as e:
            print(f"Error scraping DOU jobs: {e}")
        finally:
            driver.quit()

        return jobs

    def parse_job_element(
        self,
        element: WebElement,
        skip_positions: List[str],
        preffered_positions: List[str],
    ) -> Optional[Job]:
        title = element.find_element(By.CLASS_NAME, "vt").text

        if preffered_positions and not any(
            preffered.lower() in title.lower() for preffered in preffered_positions
        ):
            raise SkipJobException(
                f"Job title '{title}' does not match preferred positions."
            )

        if any(skip in title.lower() for skip in skip_positions):
            raise SkipJobException(f"Job title '{title}' contains a skip keyword.")

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

    def save_jobs_to_db(self, jobs: List[Job]) -> int:
        saved_count = 0
        with sqlite3.connect(self.db_path) as conn:
            for job in jobs:
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
                    saved_count += 1
                except sqlite3.IntegrityError:
                    # skip duplicate jobs
                    continue
            return saved_count

    def get_jobs(self) -> List[Job]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT title, description, company, link, location, salary, date_posted FROM jobs ORDER BY created_at DESC"
            )
            return [Job(*row) for row in cursor.fetchall()]

    def scrape_and_save(
        self, category: str, skip_positions: List[str] = [], preferred_postions=[]
    ) -> int:
        jobs = self.scrape_dou_jobs(category, skip_positions, preferred_postions)
        saved_count = self.save_jobs_to_db(jobs)
        print(f"Scraped {len(jobs)} jobs, saved {saved_count} new jobs")
        return saved_count


if __name__ == "__main__":
    scrapper = JobScraper("jobs.db")
    scrapper.scrape_and_save("DevOps")
    scrapper.scrape_and_save(
        "Support", preferred_postions=["tech", "technical"], skip_positions=["customer"]
    )

    jobs = scrapper.get_jobs()
    for job in jobs:
        print(f"{job.title} at {job.company} ({job.location}) - {job.link}")
