"use client";
import Link from "next/link";
import type { JobFilters, JobItem } from "@/types/job";
import { JOB_STATUSES, WORK_MODES } from "@/types/job";

export default function JobsList({
  items,
  total,
  filters,
  loading,
  onFiltersChange,
  onAdd,
}: {
  items: JobItem[];
  total: number;
  filters: JobFilters;
  loading: boolean;
  onFiltersChange: (next: JobFilters) => void;
  onAdd: () => void;
}) {
  const apply = (patch: Partial<JobFilters>) => onFiltersChange({ ...filters, ...patch, page: 1 });

  return (
    <div>
      <div className="job-toolbar">
        <input
          placeholder="Search title, company, location…"
          value={filters.search ?? ""}
          onChange={(e) => apply({ search: e.target.value })}
          className="job-search"
        />
        <select value={filters.status ?? ""} onChange={(e) => apply({ status: e.target.value })}>
          <option value="">All statuses</option>
          {JOB_STATUSES.map((s) => <option value={s} key={s}>{s}</option>)}
        </select>
        <select value={filters.work_mode ?? ""} onChange={(e) => apply({ work_mode: e.target.value })}>
          <option value="">All work modes</option>
          {WORK_MODES.filter(Boolean).map((w) => <option value={w} key={w}>{w}</option>)}
        </select>
        <select value={filters.sort ?? "newest"} onChange={(e) => apply({ sort: e.target.value })}>
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="company">Company A–Z</option>
          <option value="title">Title A–Z</option>
        </select>
        <button className="btn" onClick={onAdd}>Add job</button>
      </div>

      <div className="muted job-count">{total} job{total === 1 ? "" : "s"}</div>

      {loading ? (
        <div className="upload-status"><span className="spinner" aria-hidden />Loading jobs…</div>
      ) : items.length === 0 ? (
        <div className="card empty-state">
          <h3>No jobs match</h3>
          <p className="muted">Add a job by URL, pasted description, or manual entry to get started.</p>
          <button className="btn secondary" onClick={onAdd} style={{ marginTop: 12 }}>Add your first job</button>
        </div>
      ) : (
        <div className="job-grid">
          {items.map((job) => (
            <Link className="job-card" href={`/jobs/${job.id}`} key={job.id}>
              <div className="job-card-head">
                <strong className="ellipsis" title={job.title}>{job.title}</strong>
                <span className={`badge status-${job.status.toLowerCase()}`}>{job.status}</span>
              </div>
              <div className="muted">{job.company || "No company"}{job.location ? ` · ${job.location}` : ""}</div>
              <div className="job-tags">
                {job.work_mode && <span className="chip">{job.work_mode}</span>}
                {job.employment_type && <span className="chip">{job.employment_type}</span>}
                {job.source === "URL" && <span className="chip">Imported</span>}
                {job.has_analysis ? <span className="chip chip-accent">Analyzed</span> : <span className="chip chip-dim">Not analyzed</span>}
              </div>
              <div className="muted job-date">{formatDate(job.created_at)}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}