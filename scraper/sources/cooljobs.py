import re
import time
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.models import RawOpportunity, SourceResult
from scraper.sources.base import JobSource


class CoolJobsSource(JobSource):
    name = "cooljobs"

    def __init__(self, config: dict, client: httpx.Client | None = None):
        self.config = config
        self.search_url = config["search_url"]
        self.delay = float(config.get("request_delay_seconds", 0.35))
        self.client = client or httpx.Client(
            timeout=float(config.get("timeout_seconds", 30)),
            follow_redirects=True,
            headers={"User-Agent": "CzechOpportunityRadar/0.1 (+https://github.com/kovacoj/jobs)"},
        )

    def fetch(self) -> SourceResult:
        try:
            response = self.client.get(self.search_url)
            response.raise_for_status()
            urls = self.parse_search(response.text, self.search_url)
            soup = BeautifulSoup(response.text, "html.parser")
            next_button = soup.select_one("#feed_loadnext[data-nextdata]")
            next_data = next_button.get("data-nextdata") if next_button else None
            pages = 1
            while next_data and pages < int(self.config.get("max_pages", 10)):
                page = self.client.post(self.search_url, data={"action": "FeedNext", "nextdata": next_data})
                page.raise_for_status()
                payload = page.json()
                urls.extend(self.parse_search_fragment(payload.get("html", ""), self.search_url))
                next_data = payload.get("nextdata")
                pages += 1
            urls = list(dict.fromkeys(urls))
            jobs = []
            for url in urls:
                if self.delay:
                    time.sleep(self.delay)
                detail = self.client.get(url)
                detail.raise_for_status()
                job = self.parse_detail(detail.text, url)
                if job.active:
                    jobs.append(job)
            return SourceResult(source=self.name, jobs=jobs, success=True)
        except Exception as exc:
            return SourceResult(source=self.name, success=False, error=f"{type(exc).__name__}: {exc}")

    @staticmethod
    def parse_search(html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        base = soup.select_one("base[href]")
        detail_base = base.get("href") if base else urljoin(base_url, "/en/")
        return [urljoin(detail_base, row.get("href", "")) for row in soup.select("#positions-list > a.row[href]")]

    @staticmethod
    def parse_search_fragment(html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        detail_base = urljoin(base_url, "/en/")
        return [urljoin(detail_base, row.get("href", "")) for row in soup.select("a.row[href]")]

    @staticmethod
    def parse_detail(html: str, url: str) -> RawOpportunity:
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.select_one("h1")
        if heading is None:
            raise ValueError("missing job title")
        source_id_match = re.search(r"\((\d+)\)\s*$", heading.get_text(" ", strip=True))
        source_id = source_id_match.group(1) if source_id_match else None
        title = re.sub(r"\s*\(\d+\)\s*$", "", heading.get_text(" ", strip=True)).strip()
        fields = {}
        for field in soup.select(".form-padding > .field"):
            label = field.select_one("label")
            value = field.select_one("div")
            if label and value:
                fields[label.get_text(" ", strip=True).casefold()] = value.get_text(" ", strip=True)
        body = soup.select_one(".body")
        description = body.get_text("\n", strip=True) if body else ""
        active = soup.select_one(".archived-position-warning") is None
        salary_min, salary_max, currency = _parse_compensation(fields.get("monthly"))
        return RawOpportunity(
            source="cooljobs",
            source_id=source_id,
            title=title,
            company="CoolPeople",
            url=url,
            description=description,
            location=fields.get("location"),
            remote_percentage=_parse_percentage(fields.get("home office")),
            contract_text=fields.get("contract"),
            project_duration_months=_parse_duration(fields.get("start (lenght)") or fields.get("start (length)")),
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            compensation_period="month" if salary_max is not None else None,
            active=active,
        )


def _parse_percentage(value: str | None) -> int | None:
    match = re.search(r"(\d{1,3})\s*%", value or "")
    return min(100, int(match.group(1))) if match else None


def _parse_duration(value: str | None) -> float | None:
    match = re.search(r"\((\d+(?:[.,]\d+)?)\s*m", value or "", re.IGNORECASE)
    return float(match.group(1).replace(",", ".")) if match else None


def _parse_compensation(value: str | None) -> tuple[float | None, float | None, str | None]:
    if not value:
        return None, None, None
    currency_match = re.search(r"\b(CZK|EUR|USD)\b", value, re.IGNORECASE)
    numbers = re.findall(r"\d[\d\s.,]*", value)
    amounts = [float(re.sub(r"[^\d.]", "", number.replace(",", "."))) for number in numbers]
    currency = currency_match.group(1).upper() if currency_match else None
    return (min(amounts), max(amounts), currency) if amounts else (None, None, currency)
