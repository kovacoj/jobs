# Czech AI/Data Opportunity Radar

A deterministic multi-source job collector with profile-based scoring and a static GitHub Pages frontend.

Current sources:

- CoolJobs
- Jobs.cz
- Profesia.sk

LinkedIn is recorded as unsupported because reliable collection would require login or anti-bot circumvention. Additional sources can be added behind the `JobSource` interface without changing the pipeline.

## Run locally

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m scraper.main
```

The scraper writes `data/jobs.json`, `data/runs.json`, and `data/source_status.json`. Candidate preferences live in `config/profile.yaml`; source behavior lives in `config/sources.yaml`.

The frontend is maintained separately on the `gh-pages` branch. GitHub Actions refreshes data every four hours and commits changed JSON to that branch, from which GitHub Pages deploys directly.

## Design boundaries

- Source collection and parsing are deterministic Python.
- A failed source preserves its previously active opportunities.
- Jobs missing from two successful runs become inactive.
- No browser automation, authentication bypass, or LLM is used in the first vertical slice.
- Future model evaluation belongs behind an `LLMProvider` interface and only processes new or changed jobs.
