"use client";
export default function ProfileCompleteness({ percentage, missing }: { percentage: number; missing: string[] }) {
  return (
    <div className="card">
      <h3>Profile completeness</h3>
      <div className="progress-track" role="progressbar" aria-valuenow={percentage} aria-valuemin={0} aria-valuemax={100}>
        <div className="progress-fill" style={{ width: `${percentage}%` }} />
      </div>
      <div className="muted" style={{ marginTop: 8 }}>{percentage}% complete</div>
      {missing.length > 0 && (
        <div className="missing-list">
          <div className="muted section-label">Add to improve your profile</div>
          {missing.map((m) => (
            <span className="chip" key={m}>+ {m}</span>
          ))}
        </div>
      )}
    </div>
  );
}