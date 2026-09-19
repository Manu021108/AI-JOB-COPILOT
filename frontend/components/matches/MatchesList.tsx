"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import MatchScoreRing from "@/components/matches/MatchScoreRing";
import { listMatches, runAllMatches } from "@/lib/api";
import { MATCH_CATEGORIES, MATCH_SORTS, type JobMatchListItem, type MatchFilters } from "@/types/match";

export default function MatchesList() {
  const [items, setItems] = useState<JobMatchListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState<MatchFilters>({ sort: "match", page_size: 20 });
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [generated, setGenerated] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (next: MatchFilters) => {
    setLoading(true);
    setError(null);
    try {
      const data = await listMatches(next);
      setItems(data.items);
      setTotal(data.total);
      setPage(data.page);
      setTotalPages(data.total_pages);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  const apply = (patch: Partial<MatchFilters>) => {
    const next = { ...filters, ...patch, page: 1 };
    setFilters(next);
    load(next);
  };

  const goToPage = (nextPage: number) => {
    const next = { ...filters, page: nextPage };
    setFilters(next);
    load(next);
  };

  const handleRunAll = async () => {
    if (running) return;
    setRunning(true);
    setError(null);
    try {
      const result = await runAllMatches();
      setGenerated(result.generated);
      await load({ ...filters, page: 1 });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <div className="job-toolbar">
        <input
          placeholder="Filter by company…"
          value={filters.company ?? ""}
          onChange={(e) => apply({ company: e.target.value })}
          className="job-search"
        />
        <select value={filters.category ?? ""} onChange={(e) => apply({ category: e.target.value || undefined })}>
          <option value="">All categories</option>
          {MATCH_CATEGORIES.map((c) => <option value={c} key={c}>{c.replace("_", " ")}</option>)}
        </select>
        <select value={filters.score_min ?? ""} onChange={(e) => apply({ score_min: e.target.value ? Number(e.target.value) : undefined })}>
          <option value="">Min score</option>
          <option value="85">85+</option>
          <option value="70">70+</option>
          <option value="55">55+</option>
        </select>
        <select value={filters.sort ?? "match"} onChange={(e) => apply({ sort: e.target.value })}>
          {MATCH_SORTS.map((s) => <option value={s} key={s}>{sortLabel(s)}</option>)}
        </select>
        <button className="btn" onClick={handleRunAll} disabled={running}>{running ? "Running…" : "Generate missing"}</button>
      </div>

      <div className="muted job-count">{total} match{total === 1 ? "" : "es"}
        {generated > 0 && <span className="chip chip-accent" style={{ marginLeft: 8 }}>{generated} generated</span>}
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <div className="upload-status"><span className="spinner" aria-hidden />Loading matches…</div>
      ) : items.length === 0 ? (
        <div className="card empty-state">
          <h3>No matches yet</h3>
          <p className="muted">Generate matches for your active jobs to see how they line up with your profile.</p>
          <button className="btn secondary" onClick={handleRunAll} disabled={running} style={{ marginTop: 12 }}>
            {running ? "Running…" : "Generate matches"}
          </button>
        </div>
      ) : (
        <div className="match-list">
          {items.map((item) => (
            <Link className="match-row" href={`/jobs/${item.job_id}`} key={item.id}>
              <MatchScoreRing score={item.overall_score} category={item.category} size={56} showLabel={false} />
              <div className="match-row-main">
                <strong className="ellipsis" title={item.job_title}>{item.job_title}</strong>
                <div className="muted">{item.company || "No company"}{item.location ? ` · ${item.location}` : ""}{item.work_mode ? ` · ${item.work_mode}` : ""}</div>
                <div className="job-tags" style={{ marginTop: 6 }}>
                  {item.matching_skills.slice(0, 3).map((s) => <span className="chip" key={s}>{s}</span>)}
                  {item.missing_required_skills.length > 0 && (
                    <span className="chip chip-missing">missing {item.missing_required_skills.length}</span>
                  )}
                </div>
              </div>
              <div className="match-row-side">
                <span className={`chip ${item.category === "STRONG_MATCH" ? "chip-accent" : ""}`}>{item.category.replace("_", " ")}</span>
                {item.is_stale && <span className="chip chip-missing">stale</span>}
              </div>
            </Link>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="pagination">
          <button className="btn secondary small" disabled={page <= 1} onClick={() => goToPage(page - 1)}>← Prev</button>
          <span className="muted">Page {page} of {totalPages}</span>
          <button className="btn secondary small" disabled={page >= totalPages} onClick={() => goToPage(page + 1)}>Next →</button>
        </div>
      )}
    </div>
  );
}

function sortLabel(value: string): string {
  const labels: Record<string, string> = {
    match: "Best match",
    newest: "Newest first",
    oldest: "Oldest first",
    role: "Role A–Z",
    company: "Company A–Z",
    stale: "Stale first",
  };
  return labels[value] ?? value;
}