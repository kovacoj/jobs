from pathlib import Path

from scraper.sources.jobs_cz import JobsCzSource
from scraper.sources.profesia_sk import ProfesiaSkSource

FIXTURES = Path(__file__).parent / "fixtures"


def test_jobs_cz_extracts_public_ad_urls():
    html = (FIXTURES / "jobs_cz_search.html").read_text()
    assert JobsCzSource.parse_search(html) == ["https://www.jobs.cz/rpd/2001381338/?searchId=x"]


def test_profesia_extracts_public_ad_urls():
    html = (FIXTURES / "profesia_sk_search.html").read_text()
    assert ProfesiaSkSource.parse_search(html) == ["https://www.profesia.sk/praca/example/O5354989?search_id=x"]


def test_jobs_cz_reads_structured_detail():
    html = (FIXTURES / "structured_detail.html").read_text()
    job = JobsCzSource.parse_detail(html, "https://www.jobs.cz/rpd/2001381338/")
    assert job.title == "Data Scientist / ML Engineer"
    assert job.company == "Example Labs"
    assert job.location == "Praha, CZ"
    assert job.remote_percentage == 100
    assert job.salary_min == 100000
    assert job.salary_max == 140000
    assert job.compensation_period == "month"


def test_profesia_reads_structured_detail():
    html = (FIXTURES / "structured_detail.html").read_text()
    job = ProfesiaSkSource.parse_detail(html, "https://www.profesia.sk/praca/example/O5354989")
    assert job.source_id == "5354989"
    assert job.title == "Data Scientist / ML Engineer"
    assert job.contract_text == "FULL_TIME"
