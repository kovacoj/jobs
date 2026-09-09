import json

import pytest
from pydantic import ValidationError

from scripts.run_discovery import extract_answer
from worker.models import DiscoveryRequest, DiscoveryResponse


def valid_response() -> dict:
    return {
        "run": {"searched_at": "2026-09-09T20:17:00Z", "queries": ["AI Engineer B2B Czech"], "sources_searched": ["Example"]},
        "opportunities": [{
            "title": "AI Engineer", "company": "Example", "url": "https://example.com/jobs/1",
            "source": "Example", "description": "Build an LLM service.", "country": "CZ", "city": "Prague",
            "remote": "100%", "contract_type": "b2b", "allocation": 10, "rate_min": 500,
            "rate_max": 600, "currency": "EUR", "rate_period": "md", "published_at": None,
            "required_skills": ["Python"], "preferred_skills": ["Azure"], "verification_status": "verified",
            "evidence": ["Advert explicitly says B2B and remote."], "discovery_reason": "Strong project fit."
        }],
    }


def test_sample_profile_is_valid():
    DiscoveryRequest.model_validate_json(open("tests/fixtures/sample_profile.json", encoding="utf-8").read())


def test_extracts_text_from_opencode_json_events():
    payload = json.dumps(valid_response())
    stdout = "\n".join([
        json.dumps({"type": "step_start", "part": {"type": "step-start"}}),
        json.dumps({"type": "text", "part": {"type": "text", "text": payload}}),
    ])
    assert json.loads(extract_answer(stdout))["opportunities"][0]["contract_type"] == "b2b"


def test_discovery_response_rejects_missing_url():
    payload = valid_response()
    del payload["opportunities"][0]["url"]
    with pytest.raises(ValidationError):
        DiscoveryResponse.model_validate(payload)
