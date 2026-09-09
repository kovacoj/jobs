import { useEffect, useState } from "react";

type Contract = "ico_b2b" | "freelance" | "dpp" | "dpc" | "employment" | "internship" | "unknown";

type Job = {
  id: string;
  title: string;
  company: string | null;
  source: string;
  url: string;
  location: string | null;
  remote_percentage: number | null;
  contract_type: Contract;
  project_duration_months: number | null;
  allocation_md_month: number | null;
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  compensation_period: string | null;
  technologies: string[];
  first_seen_at: string;
  score: number;
  matched_skills: string[];
  active: boolean;
};

type JobData = {
  generated_at: string | null;
  summary: { scanned: number; relevant: number; new: number };
  jobs: Job[];
};

type SourceStatus = Record<string, { success: boolean; unsupported?: boolean; last_success?: string; last_error?: string | null; job_count?: number }>;

const contracts: { value: Contract | "all"; label: string }[] = [
  { value: "all", label: "All contracts" },
  { value: "ico_b2b", label: "IČO / B2B" },
  { value: "freelance", label: "Freelance" },
  { value: "dpp", label: "DPP" },
  { value: "dpc", label: "DPČ" },
  { value: "employment", label: "Employment" },
];

const labels: Record<Contract, string> = {
  ico_b2b: "IČO / B2B",
  freelance: "Freelance",
  dpp: "DPP",
  dpc: "DPČ",
  employment: "Employment",
  internship: "Internship",
  unknown: "Contract unknown",
};

function money(job: Job) {
  if (job.salary_max == null) return "Rate not listed";
  const amount = new Intl.NumberFormat("en", { maximumFractionDigits: 0 }).format(job.salary_max);
  return `${amount} ${job.currency ?? ""} / ${job.compensation_period ?? "period"}`;
}

function relativeDate(value: string) {
  const hours = Math.floor((Date.now() - new Date(value).getTime()) / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function App() {
  const [data, setData] = useState<JobData | null>(null);
  const [sourceStatus, setSourceStatus] = useState<SourceStatus>({});
  const [error, setError] = useState("");
  const [contract, setContract] = useState<Contract | "all">("all");
  const [minimumScore, setMinimumScore] = useState(0);
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [source, setSource] = useState("all");
  const [sort, setSort] = useState("score");

  useEffect(() => {
    Promise.all([
      fetch(`${import.meta.env.BASE_URL}data/jobs.json`).then((response) => {
        if (!response.ok) throw new Error(`jobs.json returned ${response.status}`);
        return response.json() as Promise<JobData>;
      }),
      fetch(`${import.meta.env.BASE_URL}data/source_status.json`).then((response) => response.json() as Promise<SourceStatus>),
    ])
      .then(([jobs, statuses]) => {
        setData(jobs);
        setSourceStatus(statuses);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  const jobs = [...(data?.jobs ?? [])]
    .filter((job) => job.active)
    .filter((job) => contract === "all" || job.contract_type === contract)
    .filter((job) => job.score >= minimumScore)
    .filter((job) => !remoteOnly || job.remote_percentage === 100)
    .filter((job) => source === "all" || job.source === source)
    .sort((a, b) => sort === "newest"
      ? new Date(b.first_seen_at).getTime() - new Date(a.first_seen_at).getTime()
      : sort === "rate"
        ? (b.salary_max ?? -1) - (a.salary_max ?? -1)
        : b.score - a.score);

  return (
    <main>
      <header className="masthead">
        <div className="eyebrow"><span className="pulse" /> LIVE MARKET SIGNAL · CZECH REPUBLIC</div>
        <div className="title-row">
          <div>
            <h1>Opportunity<br /><em>Radar</em></h1>
            <p className="intro">AI, data and engineering contracts, ranked against your technical profile.</p>
          </div>
          <div className="scan-stamp">
            <span>LAST SWEEP</span>
            <strong>{data?.generated_at ? new Date(data.generated_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "Awaiting data"}</strong>
          </div>
        </div>
        <div className="metrics">
          <div><strong>{data?.summary.scanned ?? "—"}</strong><span>SCANNED</span></div>
          <div><strong>{data?.summary.relevant ?? "—"}</strong><span>ACTIVE</span></div>
          <div><strong>{data?.summary.new ?? "—"}</strong><span>NEW</span></div>
          <div><strong>{jobs.length}</strong><span>IN VIEW</span></div>
        </div>
      </header>

      <section className="controls" aria-label="Opportunity filters">
        <div className="contract-tabs">
          {contracts.map((item) => <button className={contract === item.value ? "active" : ""} key={item.value} onClick={() => setContract(item.value)}>{item.label}</button>)}
        </div>
        <div className="control-row">
          <label>Minimum score <strong>{minimumScore}</strong><input type="range" min="0" max="100" step="5" value={minimumScore} onChange={(event) => setMinimumScore(Number(event.target.value))} /></label>
          <label className="check"><input type="checkbox" checked={remoteOnly} onChange={(event) => setRemoteOnly(event.target.checked)} /> Remote only</label>
          <label>Source <select value={source} onChange={(event) => setSource(event.target.value)}><option value="all">All sources</option>{Object.keys(sourceStatus).filter((name) => !sourceStatus[name].unsupported).map((name) => <option value={name} key={name}>{name}</option>)}</select></label>
          <label>Order <select value={sort} onChange={(event) => setSort(event.target.value)}><option value="score">Best match</option><option value="newest">Newest</option><option value="rate">Highest rate</option></select></label>
        </div>
      </section>

      {error && <div className="error">Data feed unavailable: {error}</div>}

      <section className="feed">
        <div className="feed-heading"><span>RANK</span><span>{jobs.length} SIGNALS FOUND</span></div>
        {data && jobs.length === 0 && <div className="empty">No opportunities match these filters.</div>}
        {jobs.map((job, index) => {
          const isNew = Date.now() - new Date(job.first_seen_at).getTime() < 86_400_000;
          return <article className="job" key={job.id}>
            <div className="rank"><small>{String(index + 1).padStart(2, "0")}</small><strong>{job.score}</strong><span>/100</span></div>
            <div className="job-body">
              <div className="job-top">
                <div>
                  <div className="badges">{isNew && <span className="new">NEW</span>}<span className={job.contract_type === "ico_b2b" ? "contract primary" : "contract"}>{labels[job.contract_type]}</span><span>{job.source.toUpperCase()}</span></div>
                  <h2>{job.title}</h2>
                  <p className="company">{job.company ?? "Company undisclosed"}</p>
                </div>
                <a className="open" href={job.url} target="_blank" rel="noreferrer" aria-label={`Open ${job.title}`}>↗</a>
              </div>
              <div className="facts">
                <span><b>LOC</b>{job.location ?? "Not listed"}</span>
                <span><b>REMOTE</b>{job.remote_percentage == null ? "Unknown" : `${job.remote_percentage}%`}</span>
                <span><b>RATE</b>{money(job)}</span>
                {job.project_duration_months != null && <span><b>TERM</b>{job.project_duration_months} months</span>}
              </div>
              <div className="skills">{job.matched_skills.slice(0, 7).map((skill) => <span key={skill}>{skill}</span>)}</div>
              <div className="discovered">Discovered {relativeDate(job.first_seen_at)}</div>
            </div>
          </article>;
        })}
      </section>

      <footer>
        <div><strong>SOURCE HEALTH</strong>{Object.entries(sourceStatus).map(([name, status]) => <span key={name} className={status.success ? "healthy" : "unhealthy"}>{status.success ? "●" : "×"} {name} {status.job_count != null && `· ${status.job_count}`}</span>)}</div>
        <p>Deterministic collection. Profile-based ranking. Original adverts remain the source of truth.</p>
      </footer>
    </main>
  );
}

export default App;
