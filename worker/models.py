from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class DiscoveryRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    searched_at: datetime
    queries: list[str]
    sources_searched: list[str]


class DiscoveredOpportunity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    company: str | None
    url: HttpUrl
    source: str = Field(min_length=1)
    description: str
    country: str | None
    city: str | None
    remote: str | None
    contract_type: Literal["ico", "b2b", "freelance", "dpp", "dpc", "employment", "unknown"]
    allocation: float | None = Field(default=None, ge=0)
    rate_min: float | None = Field(default=None, ge=0)
    rate_max: float | None = Field(default=None, ge=0)
    currency: str | None
    rate_period: Literal["hour", "day", "md", "month", "year"] | None
    published_at: datetime | None
    required_skills: list[str]
    preferred_skills: list[str]
    verification_status: Literal["verified", "partial", "snippet_only"]
    evidence: list[str] = Field(min_length=1)
    discovery_reason: str = Field(min_length=1)

    @field_validator("rate_max")
    @classmethod
    def maximum_not_below_minimum(cls, value: float | None, info):
        minimum = info.data.get("rate_min")
        if value is not None and minimum is not None and value < minimum:
            raise ValueError("rate_max cannot be below rate_min")
        return value


class DiscoveryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run: DiscoveryRun
    opportunities: list[DiscoveredOpportunity]


class DiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    skills: list[str]
    preferred_roles: list[str]
    contract_preferences: list[str]
    countries: list[str]
    remote_worldwide: bool = True
    recent_queries: list[str] = Field(default_factory=list)
    existing_urls: list[str] = Field(default_factory=list)
    minimum_results: int = Field(default=5, ge=1, le=50)
