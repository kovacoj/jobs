from pathlib import Path

from scraper.sources.cooljobs import CoolJobsSource

FIXTURES = Path(__file__).parent / "fixtures"


def test_search_extracts_detail_urls():
    html = (FIXTURES / "cooljobs_search.html").read_text()
    assert CoolJobsSource.parse_search(html, "https://www.cooljobs.eu/en/search-job/1115.html") == [
        "https://www.cooljobs.eu/en/data-scientist/43560",
        "https://www.cooljobs.eu/en/data-engineer/43472",
    ]


def test_detail_extracts_project_fields():
    html = (FIXTURES / "cooljobs_detail.html").read_text()
    job = CoolJobsSource.parse_detail(html, "https://www.cooljobs.eu/en/data-scientist/43560")
    assert job.source_id == "43560"
    assert job.title == "Data Scientist"
    assert job.location == "Celá ČR, Poland, Bratislava"
    assert job.remote_percentage == 100
    assert job.contract_text == "Contract via CP"
    assert job.project_duration_months == 3
    assert job.salary_max == 5600
    assert job.currency == "EUR"
    assert job.compensation_period == "month"
    assert job.active
