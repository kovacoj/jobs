from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ContractType = Literal[
    "ico_b2b",
    "freelance",
    "dpp",
    "dpc",
    "employment",
    "internship",
    "unknown",
]


class RawOpportunity(BaseModel):
    source: str
    source_id: str | None = None
    title: str
    company: str | None = None
    url: str
    description: str = ""
    location: str | None = None
    remote_percentage: int | None = None
    contract_text: str | None = None
    project_duration_months: float | None = None
    allocation_md_month: float | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    compensation_period: str | None = None
    technologies: list[str] = Field(default_factory=list)
    active: bool = True


class Opportunity(BaseModel):
    id: str
    fingerprint: str
    source: str
    source_id: str | None
    title: str
    company: str | None
    url: str
    description: str
    country: str | None
    city: str | None
    location: str | None
    remote_percentage: int | None
    contract_type: ContractType
    contract_evidence: str | None
    project_duration_months: float | None
    allocation_md_month: float | None
    salary_min: float | None
    salary_max: float | None
    currency: str | None
    compensation_period: str | None
    technologies: list[str]
    published_at: datetime | None = None
    first_seen_at: datetime
    discovered_at: datetime
    last_seen_at: datetime
    missed_runs: int = 0
    active: bool = True
    raw_hash: str
    score: int
    matched_skills: list[str] = Field(default_factory=list)


class SourceResult(BaseModel):
    source: str
    jobs: list[RawOpportunity] = Field(default_factory=list)
    success: bool
    error: str | None = None
