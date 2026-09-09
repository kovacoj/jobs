import re
import time
from urllib.parse import urlencode, urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.models import RawOpportunity, SourceResult
from scraper.sources.base import JobSource
from scraper.sources.structured import compensation, job_posting, location_text, organization_name, plain_text, remote_percentage


class JobsCzSource(JobSource):
    name = "jobs_cz"

    def __init__(self, config: dict, client: httpx.Client | None = None):
        self.config = config
        self.client = client or httpx.Client(timeout=config.get("timeout_seconds", 30), follow_redirects=True, headers={"User-Agent": "CzechOpportunityRadar/0.1 (+https://github.com/kovacoj/jobs)"})

    def fetch(self) -> SourceResult:
        try:
            listings = {}
            for query in self.config.get("queries", []):
                for page in range(1, int(self.config.get("max_pages_per_query", 1)) + 1):
                    url = f'{self.config["search_url"]}?{urlencode({"q[]": query, "page": page})}'
                    response = self.client.get(url)
                    response.raise_for_status()
                    for job in self.parse_search_jobs(response.text):
                        listings[job.url] = job
            jobs = []
            for url, listing in list(listings.items())[: int(self.config.get("max_details", 80))]:
                try:
                    time.sleep(float(self.config.get("request_delay_seconds", 0.2)))
                    response = self.client.get(url)
                    response.raise_for_status()
                    detail = self.parse_detail(response.text, url)
                    detail.company = detail.company or listing.company
                    detail.location = detail.location or listing.location
                    detail.title = detail.title or listing.title
                    jobs.append(detail)
                except Exception:
                    jobs.append(listing)
            return SourceResult(source=self.name, jobs=jobs, success=True)
        except Exception as exc:
            return SourceResult(source=self.name, success=False, error=f"{type(exc).__name__}: {exc}")

    @staticmethod
    def parse_search(html: str) -> list[str]:
        return [job.url for job in JobsCzSource.parse_search_jobs(html)]

    @staticmethod
    def parse_search_jobs(html: str) -> list[RawOpportunity]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for link in soup.select("a[data-jobad-id][href]"):
            card = link.find_parent("article")
            company = card.select_one(".SearchResultCard__logo img[alt]") if card else None
            footer_items = card.select(".SearchResultCard__footerItem") if card else []
            location = card.select_one('[data-test="serp-locality"]') if card else None
            jobs.append(RawOpportunity(source="jobs_cz", source_id=link.get("data-jobad-id"), title=link.get_text(" ", strip=True), company=company.get("alt") if company else (footer_items[0].get_text(" ", strip=True) if footer_items else None), url=urljoin("https://www.jobs.cz", link.get("href", "")), location=location.get_text(" ", strip=True) if location else None))
        return jobs

    @staticmethod
    def parse_detail(html: str, url: str) -> RawOpportunity:
        posting = job_posting(html)
        soup = BeautifulSoup(html, "html.parser")
        source_id = str(posting.get("identifier", {}).get("value", "")) if isinstance(posting.get("identifier"), dict) else ""
        source_id = source_id or (re.search(r"/rpd/(\d+)", url).group(1) if re.search(r"/rpd/(\d+)", url) else None)
        title = plain_text(posting.get("title")) or (soup.select_one("h1").get_text(" ", strip=True) if soup.select_one("h1") else "")
        if not title:
            raise ValueError("missing job title")
        description = plain_text(posting.get("description"))
        page_text = soup.get_text(" ", strip=True)
        salary_min, salary_max, currency, period = compensation(posting.get("baseSalary"))
        return RawOpportunity(source="jobs_cz", source_id=source_id, title=title, company=organization_name(posting.get("hiringOrganization")), url=url.split("?")[0], description=description, location=location_text(posting.get("jobLocation")), remote_percentage=remote_percentage(posting, page_text), contract_text=str(posting.get("employmentType", "")), salary_min=salary_min, salary_max=salary_max, currency=currency, compensation_period=period)
