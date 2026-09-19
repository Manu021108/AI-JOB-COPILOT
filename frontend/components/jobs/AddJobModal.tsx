"use client";
import { useState } from "react";
import { createJob, createJobFromDescription, importJobFromUrl } from "@/lib/api";
import type { Job, JobInput } from "@/types/job";
import { EMPLOYMENT_TYPES, JOB_STATUSES, WORK_MODES } from "@/types/job";

type Mode = "url" | "description" | "manual";

export default function AddJobModal({ onCreated, onClose }: { onCreated: (job: Job) => void; onClose: () => void }) {
  const [mode, setMode] = useState<Mode>("url");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [url, setUrl] = useState("");
  const [desc, setDesc] = useState("");
  const [descTitle, setDescTitle] = useState("");
  const [descCompany, setDescCompany] = useState("");
  const [descLocation, setDescLocation] = useState("");
  const [form, setForm] = useState<JobInput>({
    title: "",
    company: "",
    location: "",
    employment_type: "",
    work_mode: "",
    status: "ACTIVE",
    salary_min: undefined,
    salary_max: undefined,
    application_url: "",
    description: "",
  });

  const set = (field: keyof JobInput, value: unknown) => setForm((f) => ({ ...f, [field]: value }));

  const run = async (operation: () => Promise<Job>) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const job = await operation();
      onCreated(job);
    } catch (e) {
      setError(mapJobError((e as Error).message));
    } finally {
      setBusy(false);
    }
  };

  const submitUrl = () => run(() => importJobFromUrl(url.trim()));

  const submitDescription = () =>
    run(() =>
      createJobFromDescription({
        description: desc,
        ...(descTitle.trim() ? { title: descTitle.trim() } : {}),
        ...(descCompany.trim() ? { company: descCompany.trim() } : {}),
        ...(descLocation.trim() ? { location: descLocation.trim() } : {}),
      })
    );

  const submitManual = () => {
    const payload: JobInput = {
      title: form.title,
      company: form.company ?? "",
      location: form.location || null,
      employment_type: form.employment_type || null,
      work_mode: form.work_mode || null,
      status: (form.status ?? "ACTIVE") as Job["status"],
      salary_min: num(form.salary_min),
      salary_max: num(form.salary_max),
      application_url: form.application_url || null,
      description: form.description || null,
    };
    run(() => createJob(payload));
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Add a job</h3>
          <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>

        <div className="tabs">
          {(["url", "description", "manual"] as Mode[]).map((m) => (
            <button key={m} className={mode === m ? "active" : ""} onClick={() => setMode(m)}>
              {m === "url" ? "From URL" : m === "description" ? "Paste description" : "Manual entry"}
            </button>
          ))}
        </div>

        {mode === "url" && (
          <div className="field" style={{ marginTop: 18 }}>
            <label>Job page URL</label>
            <input
              placeholder="https://careers.example.com/jobs/123"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={busy}
            />
            <p className="muted">We fetch the page, extract the description and analyze it. LinkedIn jobs can't be fetched automatically — use "Paste description" instead.</p>
          </div>
        )}

        {mode === "description" && (
          <div className="field" style={{ marginTop: 18 }}>
            <label>Job description</label>
            <textarea
              rows={8}
              placeholder="Paste the full job description…"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              disabled={busy}
            />
            <div className="row-grid">
              <div className="field">
                <label className="field-label">Title (optional override)</label>
                <input value={descTitle} onChange={(e) => setDescTitle(e.target.value)} disabled={busy} />
              </div>
              <div className="field">
                <label className="field-label">Company (optional override)</label>
                <input value={descCompany} onChange={(e) => setDescCompany(e.target.value)} disabled={busy} />
              </div>
              <div className="field">
                <label className="field-label">Location (optional override)</label>
                <input value={descLocation} onChange={(e) => setDescLocation(e.target.value)} disabled={busy} />
              </div>
            </div>
          </div>
        )}

        {mode === "manual" && (
          <div className="editor-grid" style={{ marginTop: 18 }}>
            <div className="field">
              <label>Title *</label>
              <input value={form.title ?? ""} onChange={(e) => set("title", e.target.value)} disabled={busy} />
            </div>
            <div className="field">
              <label>Company</label>
              <input value={form.company ?? ""} onChange={(e) => set("company", e.target.value)} disabled={busy} />
            </div>
            <div className="field">
              <label>Location</label>
              <input value={form.location ?? ""} onChange={(e) => set("location", e.target.value)} disabled={busy} />
            </div>
            <div className="field">
              <label>Work mode</label>
              <select value={form.work_mode ?? ""} onChange={(e) => set("work_mode", e.target.value)} disabled={busy}>
                {WORK_MODES.map((w) => <option value={w} key={w || "any"}>{w || "—"}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Employment type</label>
              <select value={form.employment_type ?? ""} onChange={(e) => set("employment_type", e.target.value)} disabled={busy}>
                {EMPLOYMENT_TYPES.map((w) => <option value={w} key={w || "any"}>{w || "—"}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Status</label>
              <select value={form.status ?? "ACTIVE"} onChange={(e) => set("status", e.target.value)} disabled={busy}>
                {JOB_STATUSES.map((s) => <option value={s} key={s}>{s}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Salary min</label>
              <input type="number" min={0} value={form.salary_min ?? ""} onChange={(e) => set("salary_min", e.target.value === "" ? undefined : Number(e.target.value))} disabled={busy} />
            </div>
            <div className="field">
              <label>Salary max</label>
              <input type="number" min={0} value={form.salary_max ?? ""} onChange={(e) => set("salary_max", e.target.value === "" ? undefined : Number(e.target.value))} disabled={busy} />
            </div>
            <div className="field grow">
              <label>Application URL</label>
              <input value={form.application_url ?? ""} onChange={(e) => set("application_url", e.target.value)} disabled={busy} />
            </div>
            <div className="field grow">
              <label>Description</label>
              <textarea rows={4} value={form.description ?? ""} onChange={(e) => set("description", e.target.value)} disabled={busy} placeholder="Optional — paste a description to enable analysis." />
            </div>
          </div>
        )}

        {error && <div className="error">{error}</div>}

        <div className="modal-actions">
          <button className="btn secondary" onClick={onClose} disabled={busy}>Cancel</button>
          {busy ? (
            <span className="upload-status"><span className="spinner" aria-hidden />Working…</span>
          ) : (
            <button
              className="btn"
              onClick={mode === "url" ? submitUrl : mode === "description" ? submitDescription : submitManual}
              disabled={
                mode === "url" ? !url.trim() : mode === "description" ? desc.trim().length < 10 : !(form.title ?? "").trim()
              }
            >
              Add job
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function num(value: unknown): number | null | undefined {
  if (value === "" || value === undefined || value === null) return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function mapJobError(message: string): string {
  const text = message.toLowerCase();
  if (text.includes("linkedin")) return "LinkedIn jobs can't be fetched automatically. Paste the description instead.";
  if (text.includes("duplicate")) return "This job is already in your list.";
  if (text.includes("robots")) return "This site blocks automatic fetching. Paste the description instead.";
  if (text.includes("not allowed") || text.includes("unreachable") || text.includes("timeout")) return "We couldn't fetch that URL. Check the address or paste the description instead.";
  if (text.includes("too many")) return "You've imported too many URLs recently. Try again in a minute.";
  if (text.includes("no readable") || text.includes("empty")) return "No job content was found on that page. Paste the description instead.";
  if (text.includes("analy")) return "We couldn't analyze this job description.";
  return text;
}