from datetime import datetime, timezone

import yaml

from scraper.models import RawOpportunity
from scraper.normalize import normalize, normalize_contract


def test_contract_normalization_recognizes_czech_forms():
    assert normalize_contract("Práce na IČO")[0] == "ico_b2b"
    assert normalize_contract("Dohoda o provedení práce")[0] == "dpp"
    assert normalize_contract("DPČ")[0] == "dpc"
    assert normalize_contract("Permanent client")[0] == "employment"


def test_normalization_is_stable_and_scores_profile_match():
    profile = yaml.safe_load(open("config/profile.yaml", encoding="utf-8"))
    raw = RawOpportunity(
        source="cooljobs",
        source_id="42",
        title="AI Engineer",
        company="Example",
        url="https://example.test/42",
        description="Python machine learning, LLM, RAG and FastAPI on Azure",
        location="Praha",
        remote_percentage=100,
        contract_text="B2B contract",
    )
    now = datetime(2026, 9, 9, tzinfo=timezone.utc)
    first = normalize(raw, profile, now)
    second = normalize(raw, profile, now)
    assert first.id == second.id
    assert first.raw_hash == second.raw_hash
    assert first.country == "CZ"
    assert first.city == "Prague"
    assert first.contract_type == "ico_b2b"
    assert first.score >= 65
    assert "Python" in first.matched_skills
