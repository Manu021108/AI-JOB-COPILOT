"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import ProtectedRoute from "@/components/ProtectedRoute";
import Sidebar from "@/components/Sidebar";
import JobEditor from "@/components/jobs/JobEditor";
import JobMatchPanel from "@/components/matches/JobMatchPanel";
import { clearToken } from "@/lib/auth";
import { analyzeJob, deleteJob, getCurrentUser, getJob, getJobAnalysis, updateJob } from "@/lib/api";
import type { Job, JobAnalysis, JobInput } from "@/types/job";
import type { User } from "@/types/auth";

export default function JobDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [user, setUser] = useState<User | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [analysis, setAnalysis] = useState<JobAnalysis | null>(null);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setError(null);
    try {
      const data = await getJob(id);
      setJob(data);
      try {
        setAnalysis(await getJobAnalysis(id));
      } catch (e) {
        if ((e as Error & { code?: string }).code === "ANALYSIS_NOT_FOUND") setAnalysis(null);
        else throw e;
      }
    } catch (e) {
      setMissing(true);
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    getCurrentUser().then(setUser).catch(() => { clearToken(); router.replace("/login"); });
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, router]);

  const handleSave = async (payload: JobInput) => {
    if (!id) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await updateJob(id, payload);
      setJob(updated);
      setEditing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleAnalyze = async () => {
    if (!id || analyzing) return;
    setAnalyzing(true);
    setError(null);
    try {
      setAnalysis(await analyzeJob(id));
      setJob(await getJob(id));
    } catch (e) {
      setError(mapJobError((e as Error).message));
    } finally {
      setAnalyzing(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    if (!window.confirm("Delete this job? The saved analysis and skills will also be removed.")) return;
    setBusy(true);
    try {
      await deleteJob(id);
      router.replace("/jobs");
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  if (!user) return <ProtectedRoute><></></ProtectedRoute>;

  return (
    <ProtectedRoute>
      <main className="dashboard">
        <Sidebar />
        <section className="content">
          <Navbar name={user.name} />
          {missing || !job ? (
            <div className="card empty-state" style={{ marginTop: 32 }}>
              <h3>Job not found</h3>
              <p className="muted">{error ?? "This job no longer exists or is not yours."}</p>
              <Link className="btn secondary" href="/jobs" style={{ marginTop: 12, display: "inline-block" }}>Back to jobs</Link>
            </div>
          ) : (
            <>
              <div className="page-head">
                <Link href="/jobs" className="back-link">← All jobs</Link>
                <h1 style={{ marginTop: 10 }}>{job.title || "Untitled Job"}</h1>
                <p className="muted">{job.company || "No company"}{job.location ? ` · ${job.location}` : ""}</p>
                <div className="job-tags" style={{ marginTop: 8 }}>
                  <span className={`badge status-${job.status.toLowerCase()}`}>{job.status}</span>
                  {job.source === "URL" && <span className="chip">Imported</span>}
                  {job.work_mode && <span className="chip">{job.work_mode}</span>}
                  {job.employment_type && <span className="chip">{job.employment_type}</span>}
                  {job.has_analysis && <span className="chip chip-accent">Analyzed</span>}
                </div>
              </div>
              {error && <div className="error banner">{error}</div>}

              {!editing && (
                <div className="job-detail-actions">
                  <button className="btn secondary" onClick={() => setEditing(true)} disabled={busy}>Edit</button>
                  <button className="btn secondary" onClick={handleAnalyze} disabled={analyzing || !job.description?.trim()}>
                    {analyzing ? "Analyzing…" : "Re-analyze"}
                  </button>
                  <button className="btn danger" onClick={handleDelete} disabled={busy}>Delete</button>
                </div>
              )}

              {editing ? (
                <JobEditor job={job} busy={busy} onSave={handleSave} onCancel={() => setEditing(false)} />
              ) : (
                <div className="job-detail">
                  <div className="card">
                    <h3>Details</h3>
                    <div className="detail-grid">
                      <Detail label="Experience" value={job.experience_min != null || job.experience_max != null ? `${job.experience_min ?? "?"}–${job.experience_max ?? "?"} years` : null} />
                      <Detail label="Salary" value={salaryText(job)} />
                      <Detail label="Apply" value={job.application_url} link />
                      <Detail label="Posted" value={job.posted_at} />
                      <Detail label="Added" value={job.created_at} />
                      <Detail label="Source" value={job.source} />
                    </div>
                    {job.description ? (
                      <>
                        <div className="section-label">Description</div>
                        <pre className="job-desc">{job.description}</pre>
                      </>
                    ) : (
                      <p className="muted">No description saved.</p>
                    )}
                  </div>

                  {analysis ? (
                    <div className="analysis-grid">
                      {analysis.summary && <AnalysisCard label="Summary"><p style={{ margin: 0, lineHeight: 1.55 }}>{analysis.summary}</p></AnalysisCard>}
                      {analysis.required_skills.length > 0 && <AnalysisCard label="Required skills"><Chips values={analysis.required_skills} /></AnalysisCard>}
                      {analysis.tools_and_technologies.length > 0 && <AnalysisCard label="Tools & technologies"><Chips values={analysis.tools_and_technologies} /></AnalysisCard>}
                      {analysis.preferred_skills.length > 0 && <AnalysisCard label="Preferred"><Chips values={analysis.preferred_skills} /></AnalysisCard>}
                      {analysis.nice_to_have.length > 0 && <AnalysisCard label="Nice to have"><Chips values={analysis.nice_to_have} /></AnalysisCard>}
                      {analysis.responsibilities.length > 0 && <AnalysisCard label="Responsibilities"><List values={analysis.responsibilities} /></AnalysisCard>}
                      {analysis.qualifications.length > 0 && <AnalysisCard label="Qualifications"><List values={analysis.qualifications} /></AnalysisCard>}
                      {analysis.education_requirements.length > 0 && <AnalysisCard label="Education"><List values={analysis.education_requirements} /></AnalysisCard>}
                      {analysis.experience_requirements.length > 0 && <AnalysisCard label="Experience required"><List values={analysis.experience_requirements} /></AnalysisCard>}
                      {analysis.employment_details && <AnalysisCard label="Employment details"><p style={{ margin: 0 }}>{analysis.employment_details}</p></AnalysisCard>}
                    </div>
                  ) : (
                    <button className="card empty-state" onClick={handleAnalyze} disabled={analyzing || !job.description?.trim()}>
                      <h3>{job.description?.trim() ? "No analysis yet" : "No description to analyze"}</h3>
                      <p className="muted">{job.description?.trim() ? "Run analysis to extract requirements, skills and experience." : "Add a description, then you can analyze this job."}</p>
                    </button>
                  )}

                  {!editing && <JobMatchPanel jobId={id} />}
                </div>
              )}
            </>
          )}
        </section>
      </main>
    </ProtectedRoute>
  );
}

function Detail({ label, value, link }: { label: string; value: string | null | undefined; link?: boolean }) {
  if (!value) return null;
  return (
    <div>
      <div className="field-label">{label}</div>
      {link ? (
        <a className="detail-link" href={value} target="_blank" rel="noreferrer">{value}</a>
      ) : (
        <div>{formatValue(value)}</div>
      )}
    </div>
  );
}

function AnalysisCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3>{label}</h3>
      {children}
    </div>
  );
}

function Chips({ values }: { values: string[] }) {
  return <div className="chips">{values.map((v) => <span className="chip" key={v}>{v}</span>)}</div>;
}

function List({ values }: { values: string[] }) {
  return (
    <ul className="detail-list">
      {values.map((v) => <li key={v}>{v}</li>)}
    </ul>
  );
}

function formatValue(value: string): string {
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) return new Date(value).toLocaleDateString();
  return value;
}

function salaryText(job: Job): string | null {
  if (job.salary_min == null && job.salary_max == null) return null;
  const fmt = (n: number | null) => (n == null ? "?" : n.toLocaleString());
  const currency = [job.salary_currency, "USD"].find(Boolean);
  return `${fmt(job.salary_min)}–${fmt(job.salary_max)} ${currency}`;
}

function mapJobError(message: string): string {
  const text = message.toLowerCase();
  if (text.includes("no description")) return "Add a description to this job before analyzing.";
  if (text.includes("analy")) return "We couldn't analyze this job description. Try again.";
  return text;
}