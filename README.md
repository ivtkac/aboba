# aboba

Web scrapper for vacancies in jobs.dou.ua and work.ua. Now it works also for djinni (be careful)🚀.

## Installation

### Prerequisites
- Python 3.10 or higher
- Chrome/Chromium browser installed
- pip or uv package manager

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd aboba-l
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
# OR using uv
uv sync
```

## Basic Usage

### Command Line

The simplest way to use the scraper:

```bash
python src/main.py --site dou work --category "Python" "JavaScript"
```

**What this does:**
- Scrapes jobs.dou.ua for Python and JavaScript positions
- Scrapes work.ua for Python and JavaScript positions
- Stores results in `jobs.db` (SQLite database)

### View Help

```bash
python src/main.py --help
```

### Examples

**Scrape single site, single category:**
```bash
python src/main.py --site dou --category "Python"
```

**Scrape multiple sites, multiple categories:**
```bash
python src/main.py --site dou work djinni --category "Python" "DevOps" "JavaScript"
```

**Use custom database:**
```bash
python src/main.py --site dou --category "Python" --db my_jobs.db
```

**Enable verbose logging:**
```bash
python src/main.py --site dou --category "Python" --verbose
```

**Show browser window (non-headless):**
```bash
python src/main.py --site dou --category "Python" --no-headless
```

## Programmatic Usage

### Simple Script

Create a file `scrape_jobs.py`:

```python
from builder import JobScraperBuilder
from strategies import Site

# Create builder
builder = JobScraperBuilder()

# Add scrapers
builder.add_scraper(Site.DOU, "Python")
builder.add_scraper(Site.WORK, "JavaScript")

# Execute scraping
total = builder.execute()
print(f"Inserted {total} jobs into the database")
```

Run it:
```bash
python scrape_jobs.py
```

### Using Context Manager (Recommended)

```python
from builder import JobScraperBuilder
from strategies import Site

with JobScraperBuilder() as builder:
    builder.add_scraper(Site.DOU, "Python")
    builder.add_scraper(Site.WORK, "JavaScript")
    total = builder.execute()
    print(f"Inserted {total} jobs")
# Automatic cleanup
```

### Method Chaining

```python
from builder import JobScraperBuilder
from strategies import Site

total = (JobScraperBuilder()
    .add_scraper(Site.DOU, "Python")
    .add_scraper(Site.WORK, "JavaScript")
    .add_scraper(Site.DJINNI, "DevOps")
    .execute())

print(f"Total jobs: {total}")
```

## Query the Database

### Get All Jobs

```python
from repositories import JobRepository

repo = JobRepository("jobs.db")
jobs = repo.get_all()

for job in jobs:
    print(f"{job.title} at {job.company} ({job.location})")
```

### Filter Jobs

```python
from repositories import JobRepository, JobFilters

repo = JobRepository("jobs.db")

# Filter by location
kyiv_jobs = repo.get_all(JobFilters(location="Київ"))

# Filter by company
google_jobs = repo.get_all(JobFilters(company="Google"))

# Filter by title keyword
senior_jobs = repo.get_all(JobFilters(title="Senior"))

# Combine filters
filters = JobFilters(
    location="Київ",
    company="Google",
    title="Senior"
)
specific_jobs = repo.get_all(filters)
```

### Get Job Statistics

```python
from repositories import JobRepository, JobFilters

repo = JobRepository("jobs.db")

# Total jobs
total = repo.count()
print(f"Total jobs: {total}")

# Jobs in specific location
kyiv = repo.count(JobFilters(location="Київ"))
print(f"Jobs in Kyiv: {kyiv}")

# Get specific job by link
job = repo.get_by_link("https://example.com/job/123")
if job:
    print(f"Found: {job.title}")
```

## Supported Sites

| Site | Name | URL |
|------|------|-----|
| DOU | jobs.dou.ua | https://jobs.dou.ua/vacancies/ |
| Work.ua | work.ua | https://www.work.ua/jobs |
| First Job DOU | first-job.dou.ua | https://jobs.dou.ua/first-job |
| Djinni | djinni.co | https://djinni.co/jobs |

Use these names with `--site` argument:
- `dou`
- `work`
- `first-job`
- `djinni`

## Common Workflows

### Daily Scraping

Create `daily_scrape.py`:

```python
import logging
from datetime import datetime
from builder import JobScraperBuilder
from strategies import Site

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Starting daily job scrape")

with JobScraperBuilder() as builder:
    builder.add_scraper(Site.DOU, "Python")
    builder.add_scraper(Site.WORK, "Python")
    total = builder.execute()

logger.info(f"Completed: {total} jobs inserted at {datetime.now()}")
```

Run with cron:
```bash
0 9 * * * cd /path/to/aboba && python daily_scrape.py
```

### Track Job Market Trends

```python
from repositories import JobRepository, JobFilters
from datetime import datetime

repo = JobRepository("jobs.db")

# Count jobs by company
companies = {}
for job in repo.get_all():
    companies[job.company] = companies.get(job.company, 0) + 1

# Top 10 companies hiring
top_companies = sorted(companies.items(), key=lambda x: x[1], reverse=True)[:10]

print("Top 10 hiring companies:")
for company, count in top_companies:
    print(f"  {company}: {count} jobs")

# Jobs by location
locations = {}
for job in repo.get_all():
    loc = job.location or "Remote"
    locations[loc] = locations.get(loc, 0) + 1

print("\nJobs by location:")
for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True):
    print(f"  {loc}: {count} jobs")
```

### Export to CSV

```python
import csv
from repositories import JobRepository

repo = JobRepository("jobs.db")
jobs = repo.get_all()

with open("jobs_export.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Title", "Company", "Location", "Salary",
        "Date Posted", "Link", "Description"
    ])

    for job in jobs:
        writer.writerow([
            job.title,
            job.company,
            job.location or "N/A",
            job.salary or "N/A",
            job.date_posted or "N/A",
            job.link,
            job.description[:100] + "..."
        ])

print(f"Exported {len(jobs)} jobs to jobs_export.csv")
```

## Troubleshooting

### Chrome not found

**Error:** `chromedriver not found` or similar

**Solution:**
```bash
# Install selenium and chromedriver
pip install webdriver-manager
```

Then update your code:
```python
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver

# In your application, selenium will auto-download chromedriver
```

### Database locked

**Error:** `database is locked`

**Solution:** Wait or use timeout:
```python
import sqlite3
conn = sqlite3.connect("jobs.db", timeout=30.0)
```

### Memory issues with large scraping

**Solution:** Scrape in batches:
```python
scrapers = [
    (Site.DOU, "Python"),
    (Site.DOU, "JavaScript"),
    (Site.WORK, "Python"),
]

for site, category in scrapers:
    with JobScraperBuilder() as builder:
        builder.add_scraper(site, category)
        builder.execute()
    # Memory freed after each batch
```

## Next Steps

1. **Explore the codebase** - Check `REFACTORING.md` for architecture details
2. **Read usage examples** - See `USAGE_EXAMPLES.md` for advanced patterns
3. **Add more scrapers** - Extend `strategies.py` for new websites
4. **Build a web UI** - Use Flask to create a job search interface
5. **Schedule scraping** - Use APScheduler or cron for automated scraping

## Project Structure

```
aboba/
├── src/
│   ├── main.py           # CLI entry point
│   ├── builder.py        # Builder and factory patterns
│   ├── strategies.py     # Scraper implementations
│   ├── repositories.py   # Database layer
│   └── utils.py          # Utility functions
├── jobs.db               # SQLite database (created on first run)
├── README.md             # Project overview
└── pyproject.toml        # Project configuration
```

## Getting Help

- **Command line help:** `python src/main.py --help`
- **Code documentation:** Check docstrings in source files
- **Examples:** See `USAGE_EXAMPLES.md`
- **Architecture:** See `REFACTORING.md`

## Tips for Success

1. **Start small**: Begin with one site and category
2. **Check logs**: Use `--verbose` to see detailed output
3. **Database backup**: Keep backups of `jobs.db` before large scrapes
4. **Respect websites**: Add delays between requests if needed
5. **Monitor resources**: Watch CPU/memory for long-running scrapes
6. **Use context managers**: They ensure proper cleanup
7. **Handle exceptions**: Wrap scraping in try-except blocks

Happy scraping! 🚀
