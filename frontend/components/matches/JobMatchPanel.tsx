"use client";
import { useCallback, useEffect, useState } from "react";
import MatchScoreRing, { CATEGORY_LABELS } from "@/components/matches/MatchScoreRing";
import { calculateJobMatch, getJobMatch } from "@/lib/api";
import type { MatchResponse } from "@/types/match";

const SCORE_LABELS: { key: keyof MatchResponse["scores"]; label: string }[] = [
  { key: "skill", label: "Skills" },
  { key: "role", label: "Role" },
  { key: "experience", label: "Experience" },
  { key: "project", label: "Projects" },
  { key: "education", label: "Education" },
  { key: "location", label: "Location" },
  { key: "semantic", label: "Semantic" },
];

export default function JobMatchPanel({ jobId }: { jobId: string }) {
  const [match, setMatch] = useState<MatchResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);

  const load = useCallback(async () => {
    if (!jobId) return;
    try {
      setMatch(await getJobMatch(jobId));
    } catch (e) {
      if ((e as Error & { code?: string }).code === "MATCH_NOT_FOUND") setMatch(null);
      else setError((e as Error).message);
    } finally {
      setChecked(true);
    }
  }, [jobId]);

  useEffect(() => {
    setChecked(false);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  const handleCalculate = async () => {
    if (!jobId || busy) return;
    setBusy(true);
    setError(null);
    try {
      setMatch(await calculateJobMatch(jobId));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <div className="match-panel-head">
        <h3 style={{ margin: 0 }}>Match Analysis</h3>
        <button className="btn secondary" onClick={handleCalculate} disabled={busy}>
          {busy ? "Working…" : match ? "Recalculate match" : "Calculate match"}
        </button>
      </div>
      {error && <p className="error" style={{ marginTop: 10 }}>{error}</p>}
      {!checked && <div className="upload-status" style={{ marginTop: 14 }}><span className="spinner" aria-hidden />Checking match…</div>}
      {checked && !match && (
        <p className="muted" style={{ margin: "14px 0 0" }}>
          No match has been computed for this job yet. Generate one to see how well this job fits your profile.
        </p>
      )}
      {checked && match && (
        <div className="match-panel">
          <div className="match-hero">
            <MatchScoreRing score={match.overall_score} category={match.category} />
            <div>
              <div className="match-category">{CATEGORY_LABELS[match.category] ?? match.category}</div>
              <div className="muted" style={{ fontSize: 13 }}>
                Match v{match.match_version}
                {match.is_stale ? " · Profile changed" : " · up to date"}
              </div>
              {match.is_stale && (
                <div className="match-stale">Your profile changed since this match. Recalculate to refresh it.</div>
              )}
            </div>
          </div>

          <div className="match-scores">
            {SCORE_LABELS.map(({ key, label }) => (
              <div className="match-score" key={key}>
                <span className="muted">{label}</span>
                <strong>{match.scores[key] == null ? "—" : Math.round(match.scores[key]!)}</strong>
              </div>
            ))}
          </div>

          <div className="match-grid">
            <MatchBlock title="Skills you have">
              {match.matching_skills.length > 0 ? (
                <Chips values={match.matching_skills} />
              ) : (
                <p className="muted">No required skills matched.</p>
              )}
            </MatchBlock>
            <MatchBlock title="Skills you're missing">
              {match.missing_required_skills.length > 0 ? (
                <Chips values={match.missing_required_skills} danger />
              ) : (
                <p className="muted">All required skills are covered.</p>
              )}
            </MatchBlock>
          </div>

          {match.explanation && (
            <MatchBlock title="Why this score?">
              <p style={{ margin: 0, lineHeight: 1.6 }}>{match.explanation}</p>
            </MatchBlock>
          )}

          <div className="match-grid">
            {match.strengths.length > 0 && (
              <MatchBlock title="Strengths">
                <ul className="detail-list">{match.strengths.map((s) => <li key={s}>{s}</li>)}</ul>
              </MatchBlock>
            )}
            {match.gaps.length > 0 && (
              <MatchBlock title="Gaps to close">
                <ul className="detail-list">{match.gaps.map((g) => <li key={g}>{g}</li>)}</ul>
              </MatchBlock>
            )}
          </div>

          {match.relevant_projects.length > 0 && (
            <MatchBlock title="Relevant projects">
              <ul className="detail-list">
                {match.relevant_projects.map((p) => (
                  <li key={p.project}><strong>{p.project}</strong><span className="muted"> — {p.reason}</span></li>
                ))}
              </ul>
            </MatchBlock>
          )}

          <div className="match-align">
            {[match.role_alignment, match.experience_alignment, match.education_alignment, match.location_alignment, match.project_alignment]
              .filter((a) => a?.status && a.status !== "neutral")
              .map((a, index) => (
                <span className={`chip chip-align-${String(a!.status).toLowerCase().replace(/[^a-z]/g, "")}`} key={`${a!.status}-${index}`}>
                  {a!.reason}
                </span>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MatchBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="match-block">
      <div className="section-label" style={{ marginTop: 0 }}>{title}</div>
      {children}
    </div>
  );
}

function Chips({ values, danger }: { values: string[]; danger?: boolean }) {
  return (
    <div className="chips">
      {values.map((v) => (
        <span className={`chip${danger ? " chip-missing" : ""}`} key={v}>{v}</span>
      ))}
    </div>
  );
}