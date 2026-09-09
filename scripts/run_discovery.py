#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

from pydantic import ValidationError

from worker.models import DiscoveryRequest, DiscoveryResponse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SERVER = "http://127.0.0.1:4096"
DEFAULT_MODEL = "siemens/code-agentic"


def build_prompt(request: DiscoveryRequest, previous_error: str | None = None) -> str:
    schema = DiscoveryResponse.model_json_schema()
    repair = f"\nYour previous response failed validation: {previous_error}. Correct it." if previous_error else ""
    return f"""Run a fresh web discovery for paid AI/data opportunities.

Candidate/search input:
{request.model_dump_json(indent=2)}

Requirements:
- Return at least {request.minimum_results} currently actionable opportunities when the public web provides them.
- Prioritize projects, B2B, freelance, DPP/DPČ, reduced allocation, and remote work.
- Use adaptive search queries derived from the profile.
- Do not return URLs listed in existing_urls unless materially changed.
- Record every query and represented source in run metadata.
- Verify promising pages with webfetch; downgrade verification_status when full verification is impossible.
- Output exactly one JSON object conforming to this JSON Schema:
{json.dumps(schema, ensure_ascii=False)}
{repair}
"""


def extract_answer(stdout: str) -> str:
    texts: list[str] = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            part = event.get("part")
            if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                texts.append(part["text"])
            elif event.get("type") == "text" and isinstance(event.get("text"), str):
                texts.append(event["text"])
    if not texts:
        raise ValueError("OpenCode returned no final text event")
    return "".join(texts).strip()


def invoke(prompt: str, server: str, model: str) -> str:
    command = [
        "opencode", "run", "--attach", server, "--agent", "job-discovery",
        "--model", model, "--format", "json", prompt,
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=900, check=False)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"OpenCode failed ({result.returncode}): {detail[-2000:]}")
    return extract_answer(result.stdout)


def discover(request: DiscoveryRequest, server: str, model: str) -> DiscoveryResponse:
    error = None
    for attempt in range(2):
        try:
            answer = invoke(build_prompt(request, error), server, model)
            return DiscoveryResponse.model_validate_json(answer)
        except (ValueError, ValidationError) as exc:
            error = str(exc)
            if attempt == 1:
                raise
    raise RuntimeError("unreachable")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run and validate OpenCode opportunity discovery")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    try:
        request = DiscoveryRequest.model_validate_json(args.input.read_text(encoding="utf-8"))
        response = discover(request, args.server, args.model)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(response.model_dump_json(indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"Discovery failed: {exc}", file=sys.stderr)
        return 1
    print(f"Validated {len(response.opportunities)} opportunities -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
