"use client";
import { useState } from "react";
import type { Job, JobInput } from "@/types/job";
import { EMPLOYMENT_TYPES, JOB_STATUSES, WORK_MODES } from "@/types/job";

export default function JobEditor({
  job,
  busy,
  onSave,
  onCancel,
}: {
  job: Job;
  busy: boolean;
  onSave: (payload: JobInput) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<JobInput>({
    title: job.title,
    company: job.company,
    location: job.location,
    employment_type: job.employment_type ?? "",
    work_mode: job.work_mode ?? "",
    status: job.status,
    salary_min: job.salary_min ?? undefined,
    salary_max: job.salary_max ?? undefined,
    salary_currency: job.salary_currency ?? "",
    application_url: job.application_url ?? "",
    description: job.description ?? "",
  });

  const set = (field: keyof JobInput, value: unknown) => setForm((f) => ({ ...f, [field]: value }));

  const submit = () => {
    onSave({
      title: form.title,
      company: form.company ?? "",
      location: form.location || null,
      employment_type: form.employment_type || null,
      work_mode: form.work_mode || null,
      status: form.status as Job["status"],
      salary_min: num(form.salary_min),
      salary_max: num(form.salary_max),
      salary_currency: form.salary_currency || null,
      application_url: form.application_url || null,
      description: form.description || null,
    });
  };

  return (
    <div className="card editor">
      <div className="editor-grid">
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
        <div className="field">
          <label>Salary currency</label>
          <input maxLength={3} value={form.salary_currency ?? ""} onChange={(e) => set("salary_currency", e.target.value.toUpperCase())} disabled={busy} />
        </div>
        <div className="field grow">
          <label>Application URL</label>
          <input value={form.application_url ?? ""} onChange={(e) => set("application_url", e.target.value)} disabled={busy} />
        </div>
        <div className="field grow">
          <label>Description</label>
          <textarea rows={6} value={form.description ?? ""} onChange={(e) => set("description", e.target.value)} disabled={busy} />
        </div>
      </div>
      <div className="row-actions">
        <button className="btn secondary" onClick={onCancel} disabled={busy}>Cancel</button>
        <button className="btn" onClick={submit} disabled={busy || !(form.title ?? "").trim()}>
          {busy ? "Saving…" : "Save changes"}
        </button>
      </div>
    </div>
  );
}

function num(value: unknown): number | null | undefined {
  if (value === "" || value === undefined || value === null) return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}