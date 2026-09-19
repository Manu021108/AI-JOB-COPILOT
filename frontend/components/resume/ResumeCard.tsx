"use client";
import type { ResumeItem } from "@/types/resume";

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export default function ResumeCard({ resumes, onDeleted }: { resumes: ResumeItem[]; onDeleted: (id: string) => void }) {
  const active = resumes.find((r) => r.is_active);
  const history = [...resumes].sort((a, b) => b.version - a.version);

  return (
    <div className="card">
      <h3>Your resume</h3>
      {resumes.length === 0 ? (
        <p className="muted">No resume uploaded yet. Use the uploader to get started.</p>
      ) : (
        <>
          {active && (
            <div className="resume-active">
              <div>
                <strong className="ellipsis" title={active.filename}>{active.filename}</strong>
                <div className="muted">{formatSize(active.file_size)} · uploaded {formatDate(active.created_at)} · v{active.version}</div>
              </div>
              <button className="btn small danger" onClick={() => onDeleted(active.id)}>Delete</button>
            </div>
          )}
          {history.length > 1 && (
            <div className="resume-history">
              <div className="muted section-label">Version history</div>
              {history.map((r) => (
                <div className="resume-version" key={r.id}>
                  <span>v{r.version} · {formatDate(r.created_at)}</span>
                  {r.is_active ? <span className="badge">Active</span> : <button className="linkbtn" onClick={() => onDeleted(r.id)}>Delete</button>}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}