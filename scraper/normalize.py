import hashlib
import re
from datetime import datetime, timezone

from scraper.models import ContractType, Opportunity, RawOpportunity

CONTRACT_PATTERNS: list[tuple[ContractType, tuple[str, ...]]] = [
    ("dpp", (r"\bdpp\b", r"dohoda o provedení práce")),
    ("dpc", (r"\bdpč\b", r"\bdpc\b", r"dohoda o pracovní činnosti")),
    ("ico_b2b", (r"\bičo\b", r"\bosvč\b", r"živnost", r"na fakturu", r"\bb2b\b", r"contract via cp")),
    ("freelance", (r"freelanc",)),
    ("employment", (r"\bhpp\b", r"pracovní poměr", r"pracovní smlouva", r"permanent client", r"full[_ -]?time", r"plný úväzok")),
    ("internship", (r"internship", r"stáž", r"trainee")),
]

TECHNOLOGIES = (
    "Python", "Machine Learning", "Data Science", "LLM", "Generative AI", "AI Agents",
    "RAG", "API", "PyTorch", "FastAPI", "SQL", "Docker", "Git", "Azure", "n8n",
    "HPC", "OpenFOAM", "Optimization", "C++", "MPI", "PETSc", "LangChain", "LangGraph",
)


def normalize_contract(text: str | None) -> tuple[ContractType, str | None]:
    value = (text or "").casefold()
    for contract_type, patterns in CONTRACT_PATTERNS:
        for pattern in patterns:
            match = re.search(pattern, value, re.IGNORECASE)
            if match:
                return contract_type, match.group(0)
    return "unknown", None


def infer_place(location: str | None) -> tuple[str | None, str | None]:
    value = (location or "").casefold()
    if any(term in value for term in ("praha", "prague")):
        return "CZ", "Prague"
    if any(term in value for term in ("brno", "ostrava", "celá čr", "czech", "česk")):
        return "CZ", None
    if any(term in value for term in ("bratislava", "košice", "slovakia", "slovensko")):
        return "SK", "Bratislava" if "bratislava" in value else None
    return None, None


def extract_technologies(text: str) -> list[str]:
    lowered = text.casefold()
    return [technology for technology in TECHNOLOGIES if technology.casefold() in lowered]


def _stable_text(*values: object) -> str:
    return "|".join(re.sub(r"\s+", " ", str(value or "")).strip().casefold() for value in values)


def normalize(raw: RawOpportunity, profile: dict, now: datetime | None = None) -> Opportunity:
    now = now or datetime.now(timezone.utc)
    contract_type, evidence = normalize_contract(raw.contract_text)
    country, city = infer_place(raw.location)
    technologies = raw.technologies or extract_technologies(f"{raw.title} {raw.description}")
    matched, score = score_opportunity(raw, contract_type, technologies, profile)
    raw_hash = hashlib.sha256(_stable_text(
        raw.title, raw.company, raw.description, raw.location, raw.contract_text,
        raw.salary_min, raw.salary_max, raw.currency, raw.compensation_period,
    ).encode()).hexdigest()
    source_key = raw.source_id or raw.url
    return Opportunity(
        id=hashlib.sha256(f"{raw.source}:{source_key}".encode()).hexdigest()[:20],
        fingerprint=hashlib.sha256(_stable_text(raw.company, raw.title, raw.location).encode()).hexdigest()[:20],
        source=raw.source,
        source_id=raw.source_id,
        title=raw.title,
        company=raw.company,
        url=raw.url,
        description=raw.description,
        country=country,
        city=city,
        location=raw.location,
        remote_percentage=raw.remote_percentage,
        contract_type=contract_type,
        contract_evidence=evidence,
        project_duration_months=raw.project_duration_months,
        allocation_md_month=raw.allocation_md_month,
        salary_min=raw.salary_min,
        salary_max=raw.salary_max,
        currency=raw.currency,
        compensation_period=raw.compensation_period,
        technologies=technologies,
        first_seen_at=now,
        discovered_at=now,
        last_seen_at=now,
        active=raw.active,
        raw_hash=raw_hash,
        score=score,
        matched_skills=matched,
    )


def score_opportunity(raw: RawOpportunity, contract_type: ContractType, technologies: list[str], profile: dict) -> tuple[list[str], int]:
    text = f"{raw.title} {raw.description}".casefold()
    skills = profile.get("skills", {})
    weights = (("core", 4), ("strong", 3), ("bonus", 2))
    matched: list[str] = []
    skill_points = 0
    for group, weight in weights:
        for skill in skills.get(group, []):
            if str(skill).casefold() in text and skill not in matched:
                matched.append(str(skill))
                skill_points += weight
    skill_score = min(40, skill_points)
    preferred_roles = profile.get("roles", {}).get("preferred", [])
    role_score = 10 if any(role.casefold() in text for role in preferred_roles) else min(8, len(technologies) * 2)
    contract_score = {"ico_b2b": 20, "freelance": 20, "dpp": 15, "dpc": 15, "employment": 6, "unknown": 8, "internship": 0}[contract_type]
    remote = raw.remote_percentage or 0
    flexibility_score = 12 if remote == 100 else 8 if remote >= 60 else 4 if remote > 0 else 0
    if raw.allocation_md_month is not None and raw.allocation_md_month <= 12:
        flexibility_score = min(15, flexibility_score + 5)
    compensation_score = 5 if raw.salary_max is not None else 0
    return matched, min(100, skill_score + contract_score + flexibility_score + role_score + compensation_score + 5)
