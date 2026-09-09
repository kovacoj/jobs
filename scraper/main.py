import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from scraper.models import Opportunity
from scraper.normalize import normalize
from scraper.sources.cooljobs import CoolJobsSource
from scraper.sources.jobs_cz import JobsCzSource
from scraper.sources.profesia_sk import ProfesiaSkSource

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LOGGER = logging.getLogger("job-radar")


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_jobs(path: Path) -> dict[str, Opportunity]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["id"]: Opportunity.model_validate(item) for item in payload.get("jobs", [])}


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def run() -> int:
    now = datetime.now(timezone.utc)
    profile = load_yaml(ROOT / "config/profile.yaml")
    sources = load_yaml(ROOT / "config/sources.yaml")
    jobs_path = DATA_DIR / "jobs.json"
    previous = load_jobs(jobs_path)
    source_types = {"cooljobs": CoolJobsSource, "jobs_cz": JobsCzSource, "profesia_sk": ProfesiaSkSource}
    adapters = [source_types[name](config) for name, config in sources.items() if config.get("enabled") and name in source_types]
    results = [source.fetch() for source in adapters]
    jobs = []
    for result in results:
        previous_source = [job for job in previous.values() if job.source == result.source]
        if not result.success:
            jobs.extend(previous_source)
            continue
        current = [normalize(raw, profile, now) for raw in result.jobs]
        current_ids = {job.id for job in current}
        for job in current:
            old = previous.get(job.id)
            if old:
                job.first_seen_at = old.first_seen_at
                job.discovered_at = old.discovered_at
        for old in previous_source:
            if old.id in current_ids:
                continue
            old.missed_runs += 1
            old.active = old.missed_runs < 2
            current.append(old)
        jobs.extend(current)

    configured_names = {source.name for source in adapters}
    jobs.extend(job for job in previous.values() if job.source not in configured_names)

    jobs.sort(key=lambda job: (job.active, job.score, job.first_seen_at), reverse=True)
    active_count = sum(job.active for job in jobs)
    new_count = sum(job.first_seen_at == now for job in jobs)
    scanned_count = sum(len(result.jobs) for result in results)
    write_json(jobs_path, {
        "generated_at": now,
        "summary": {"scanned": scanned_count, "relevant": active_count, "new": new_count},
        "jobs": [job.model_dump(mode="json") for job in jobs],
    })

    status_path = DATA_DIR / "source_status.json"
    old_status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    for result in results:
        status = old_status.get(result.source, {})
        if result.success:
            status.update({"success": True, "last_success": str(now), "last_error": None, "job_count": len(result.jobs)})
        else:
            status.update({"success": False, "last_error": result.error, "last_attempt": str(now)})
        old_status[result.source] = status
    for name, config in sources.items():
        if config.get("status") == "unsupported":
            old_status[name] = {"success": False, "unsupported": True, "last_error": config.get("reason")}
    write_json(status_path, old_status)

    runs_path = DATA_DIR / "runs.json"
    runs = json.loads(runs_path.read_text(encoding="utf-8")) if runs_path.exists() else []
    runs.append({"ran_at": str(now), "success": all(result.success for result in results), "sources": {result.source: {"success": result.success, "discovered": len(result.jobs), "error": result.error} for result in results}, "active": active_count})
    write_json(runs_path, runs[-100:])

    for result in results:
        LOGGER.info("%s discovered=%d success=%s", result.source, len(result.jobs), result.success)
        if result.error:
            LOGGER.warning("%s error: %s", result.source, result.error)
    LOGGER.info("Total raw=%d active=%d new=%d", scanned_count, active_count, new_count)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(run())
