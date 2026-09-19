"use client";
import type { CandidateProfile } from "@/types/resume";

function List({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="section-card card">
      <h3>{label}</h3>
      {children}
    </div>
  );
}

export default function ProfileView({ profile, onEdit }: { profile: CandidateProfile; onEdit: () => void }) {
  const grouped = profile.skills.reduce<Record<string, string[]>>((acc, s) => {
    const category = s.skill_category || "Other";
    (acc[category] = acc[category] || []).push(s.skill_name);
    return acc;
  }, {});

  return (
    <div className="profile-view">
      <div className="card">
        <div className="profile-head">
          <div>
            <h2>{profile.full_name || "Candidate profile"}</h2>
            <div className="muted">
              {[profile.email, profile.phone, profile.location].filter(Boolean).join(" · ") || "No contact details"}
            </div>
            <div className="profile-links">
              {profile.linkedin_url && <a href={profile.linkedin_url} target="_blank" rel="noreferrer">LinkedIn</a>}
              {profile.github_url && <a href={profile.github_url} target="_blank" rel="noreferrer">GitHub</a>}
              {profile.portfolio_url && <a href={profile.portfolio_url} target="_blank" rel="noreferrer">Portfolio</a>}
            </div>
          </div>
          <button className="btn secondary" onClick={onEdit}>Edit profile</button>
        </div>
        {profile.professional_summary && <p className="profile-summary">{profile.professional_summary}</p>}
        <div className="profile-meta">
          {profile.target_roles.length > 0 && (
            <div>
              <span className="muted">Target roles: </span>
              {profile.target_roles.map((t) => <span className="chip" key={t}>{t}</span>)}
            </div>
          )}
          {typeof profile.years_of_experience === "number" && (
            <div className="muted">{profile.years_of_experience.toFixed(1)} years of experience</div>
          )}
          {profile.resume_id && <div className="muted">Profile built from your uploaded resume</div>}
        </div>
      </div>

      {profile.professional_summary && (
        <List label="Summary">
          <p style={{ margin: 0 }}>{profile.professional_summary}</p>
        </List>
      )}

      {Object.keys(grouped).length > 0 && (
        <List label="Skills">
          {Object.entries(grouped).map(([category, skills]) => (
            <div className="skill-group" key={category}>
              <div className="muted section-label">{category}</div>
              <div className="chips">{skills.map((s) => <span className="chip" key={s}>{s}</span>)}</div>
            </div>
          ))}
        </List>
      )}

      {profile.experience.length > 0 && (
        <List label="Experience">
          {profile.experience.map((e) => (
            <div className="entry" key={e.id}>
              <div className="entry-title">
                <strong>{e.job_title}</strong> <span>{e.employment_type}</span>
              </div>
              <div className="muted">{e.company}{e.location ? ` · ${e.location}` : ""}</div>
              {e.start_date && <div className="muted">{formatRange(e.start_date, e.end_date, e.is_current)}</div>}
              {e.description && <p className="entry-desc">{e.description}</p>}
            </div>
          ))}
        </List>
      )}

      {profile.projects.length > 0 && (
        <List label="Projects">
          {profile.projects.map((p) => (
            <div className="entry" key={p.id}>
              <div className="entry-title">
                <strong>{p.project_name}</strong>
                {p.project_url && <a href={p.project_url} target="_blank" rel="noreferrer">Open</a>}
              </div>
              {p.description && <p className="entry-desc">{p.description}</p>}
              {p.technologies.length > 0 && (
                <div className="chips">{p.technologies.map((t) => <span className="chip" key={t}>{t}</span>)}</div>
              )}
            </div>
          ))}
        </List>
      )}

      {profile.education.length > 0 && (
        <List label="Education">
          {profile.education.map((e) => (
            <div className="entry" key={e.id}>
              <div className="entry-title"><strong>{e.institution}</strong></div>
              <div className="muted">{[e.degree, e.field_of_study].filter(Boolean).join(" · ")}</div>
              {e.start_date && <div className="muted">{formatRange(e.start_date, e.end_date, false)}</div>}
              {e.grade && <div className="muted">Grade: {e.grade}</div>}
            </div>
          ))}
        </List>
      )}

      {profile.certifications.length > 0 && (
        <List label="Certifications">
          {profile.certifications.map((c) => (
            <div className="entry" key={c.id}>
              <div className="entry-title"><strong>{c.name}</strong></div>
              {c.issuing_organization && <div className="muted">{c.issuing_organization}</div>}
              {c.issue_date && <div className="muted">Issued {c.issue_date}</div>}
              {c.credential_url && <a href={c.credential_url} target="_blank" rel="noreferrer">Credential</a>}
            </div>
          ))}
        </List>
      )}
    </div>
  );
}

function formatRange(start?: string | null, end?: string | null, isCurrent?: boolean): string {
  const year = (d?: string | null) => (d ? d.slice(0, 4) : "…");
  if (end && end === start) return year(start);
  return `${year(start)} – ${isCurrent ? "Present" : year(end)}`;
}