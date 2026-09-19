"use client";
import { useState } from "react";
import type { CandidateProfile, Certification, Education, Experience, Project, Skill } from "@/types/resume";

const SKILL_CATEGORIES = ["Programming", "Backend", "Frontend", "Database", "DevOps", "AI/ML", "Data", "Other"];

function Field({ label, children, grow }: { label: string; children: React.ReactNode; grow?: boolean }) {
  return (
    <label className={`field row-field${grow ? " grow" : ""}`}>
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}

export default function Editor({ profile, onSave, onCancel }: { profile: CandidateProfile; onSave: (payload: unknown) => Promise<void>; onCancel: () => void }) {
  const [fullName, setFullName] = useState(profile.full_name ?? "");
  const [email, setEmail] = useState(profile.email ?? "");
  const [phone, setPhone] = useState(profile.phone ?? "");
  const [location, setLocation] = useState(profile.location ?? "");
  const [linkedin, setLinkedin] = useState(profile.linkedin_url ?? "");
  const [github, setGithub] = useState(profile.github_url ?? "");
  const [portfolio, setPortfolio] = useState(profile.portfolio_url ?? "");
  const [summary, setSummary] = useState(profile.professional_summary ?? "");
  const [roles, setRoles] = useState(profile.target_roles.join(", "));
  const [years, setYears] = useState(profile.years_of_experience != null ? String(profile.years_of_experience) : "");
  const [skills, setSkills] = useState<Skill[]>(profile.skills);
  const [experience, setExperience] = useState<Experience[]>(profile.experience);
  const [projects, setProjects] = useState<Project[]>(profile.projects);
  const [education, setEducation] = useState<Education[]>(profile.education);
  const [certifications, setCertifications] = useState<Certification[]>(profile.certifications);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setRow = <T,>(setter: React.Dispatch<React.SetStateAction<T[]>>, rows: T[], index: number, patch: Partial<T>) =>
    setter(rows.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  const dropRow = <T,>(setter: React.Dispatch<React.SetStateAction<T[]>>, rows: T[], index: number) =>
    setter(rows.filter((_, i) => i !== index));

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      await onSave({
        full_name: fullName || null,
        email: email || null,
        phone: phone || null,
        location: location || null,
        linkedin_url: linkedin || null,
        github_url: github || null,
        portfolio_url: portfolio || null,
        professional_summary: summary || null,
        target_roles: roles.split(",").map((r) => r.trim()).filter(Boolean),
        years_of_experience: years ? parseFloat(years) : null,
        skills: skills.filter((s) => s.skill_name.trim()).map((s) => ({ id: s.id || undefined, skill_name: s.skill_name, skill_category: s.skill_category || "Other", proficiency: s.proficiency || null })),
        experience: experience.filter((e) => e.company.trim() || e.job_title.trim()).map((e) => ({ ...e, id: e.id || undefined, description: e.description || null, location: e.location || null, employment_type: e.employment_type || null, start_date: e.start_date || null, end_date: e.end_date || null })),
        projects: projects.filter((p) => p.project_name.trim()).map((p) => ({ ...p, id: p.id || undefined, description: p.description || null, project_url: p.project_url || null, technologies: (p.technologies || []).map((t) => t.trim()).filter(Boolean), start_date: p.start_date || null, end_date: p.end_date || null })),
        education: education.filter((e) => e.institution.trim()).map((e) => ({ ...e, id: e.id || undefined, degree: e.degree || null, field_of_study: e.field_of_study || null, start_date: e.start_date || null, end_date: e.end_date || null, grade: e.grade || null })),
        certifications: certifications.filter((c) => c.name.trim()).map((c) => ({ ...c, id: c.id || undefined, issuing_organization: c.issuing_organization || null, issue_date: c.issue_date || null, expiration_date: c.expiration_date || null, credential_url: c.credential_url || null })),
      });
    } catch (e) {
      setError((e as Error).message);
      setSaving(false);
    }
  };

  const sectionHeader = (title: string, onAdd: () => void) => (
    <div className="editor-section-head">
      <h3>{title}</h3>
      <button type="button" className="btn small secondary" onClick={onAdd}>+ Add</button>
    </div>
  );

  return (
    <div className="card editor">
      <div className="profile-head">
        <h2>Edit profile</h2>
        <div>
          <button className="btn small secondary" onClick={onCancel} disabled={saving}>Cancel</button>
          <button className="btn small" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Save profile"}</button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="editor-grid">
        <Field label="Full name"><input value={fullName} onChange={(e) => setFullName(e.target.value)} /></Field>
        <Field label="Email"><input value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <Field label="Phone"><input value={phone} onChange={(e) => setPhone(e.target.value)} /></Field>
        <Field label="Location"><input value={location} onChange={(e) => setLocation(e.target.value)} /></Field>
        <Field label="LinkedIn URL"><input value={linkedin} onChange={(e) => setLinkedin(e.target.value)} /></Field>
        <Field label="GitHub URL"><input value={github} onChange={(e) => setGithub(e.target.value)} /></Field>
        <Field label="Portfolio URL"><input value={portfolio} onChange={(e) => setPortfolio(e.target.value)} /></Field>
        <Field label="Years of experience"><input type="number" min="0" step="0.5" value={years} onChange={(e) => setYears(e.target.value)} /></Field>
      </div>
      <Field label="Target roles (comma separated)"><input value={roles} onChange={(e) => setRoles(e.target.value)} /></Field>
      <Field label="Professional summary"><textarea rows={4} value={summary} onChange={(e) => setSummary(e.target.value)} /></Field>

      {sectionHeader("Skills", () => setSkills((s) => [...s, { id: "", skill_name: "", skill_category: "Other", proficiency: "" }]))}
      {skills.map((skill, i) => (
        <div className="row-grid" key={i}>
          <Field label="Skill"><input value={skill.skill_name} onChange={(e) => setRow(setSkills, skills, i, { skill_name: e.target.value })} /></Field>
          <Field label="Category">
            <select value={skill.skill_category} onChange={(e) => setRow(setSkills, skills, i, { skill_category: e.target.value })}>
              {SKILL_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Proficiency">
            <select value={skill.proficiency ?? ""} onChange={(e) => setRow(setSkills, skills, i, { proficiency: e.target.value || null })}>
              <option value="">—</option>
              <option>Beginner</option>
              <option>Intermediate</option>
              <option>Advanced</option>
            </select>
          </Field>
          <button type="button" className="btn small danger row-remove" onClick={() => dropRow(setSkills, skills, i)}>Remove</button>
        </div>
      ))}

      {sectionHeader("Experience", () => setExperience((rows) => [...rows, { id: "", company: "", job_title: "", location: "", employment_type: "", start_date: "", end_date: "", description: "", is_current: false }]))}
      {experience.map((exp, i) => (
        <div className="entry-block" key={i}>
          <div className="row-grid">
            <Field label="Company"><input value={exp.company} onChange={(e) => setRow(setExperience, experience, i, { company: e.target.value })} /></Field>
            <Field label="Job title"><input value={exp.job_title} onChange={(e) => setRow(setExperience, experience, i, { job_title: e.target.value })} /></Field>
            <Field label="Location"><input value={exp.location ?? ""} onChange={(e) => setRow(setExperience, experience, i, { location: e.target.value })} /></Field>
            <Field label="Employment type">
              <select value={exp.employment_type ?? ""} onChange={(e) => setRow(setExperience, experience, i, { employment_type: e.target.value || null })}>
                <option value="">—</option>
                <option>Full-time</option>
                <option>Part-time</option>
                <option>Contract</option>
                <option>Internship</option>
              </select>
            </Field>
            <Field label="Start date"><input type="date" value={exp.start_date ?? ""} onChange={(e) => setRow(setExperience, experience, i, { start_date: e.target.value || null })} /></Field>
            <Field label="End date"><input type="date" value={exp.end_date ?? ""} onChange={(e) => setRow(setExperience, experience, i, { end_date: e.target.value || null })} /></Field>
          </div>
          <Field label="Description"><textarea rows={2} value={exp.description ?? ""} onChange={(e) => setRow(setExperience, experience, i, { description: e.target.value })} /></Field>
          <div className="row-actions">
            <label className="check"><input type="checkbox" checked={!!exp.is_current} onChange={(e) => setRow(setExperience, experience, i, { is_current: e.target.checked, end_date: e.target.checked ? null : exp.end_date })} /> Current role</label>
            <button type="button" className="btn small danger" onClick={() => dropRow(setExperience, experience, i)}>Remove</button>
          </div>
        </div>
      ))}

      {sectionHeader("Projects", () => setProjects((rows) => [...rows, { id: "", project_name: "", description: "", technologies: [], project_url: "", start_date: "", end_date: "" }]))}
      {projects.map((p, i) => (
        <div className="entry-block" key={i}>
          <div className="row-grid">
            <Field label="Project name"><input value={p.project_name} onChange={(e) => setRow(setProjects, projects, i, { project_name: e.target.value })} /></Field>
            <Field label="Technologies (comma separated)"><input value={p.technologies.join(", ")} onChange={(e) => setRow(setProjects, projects, i, { technologies: e.target.value.split(",").map((t) => t.trim()) })} /></Field>
            <Field label="Project URL"><input value={p.project_url ?? ""} onChange={(e) => setRow(setProjects, projects, i, { project_url: e.target.value })} /></Field>
          </div>
          <Field label="Description"><textarea rows={2} value={p.description ?? ""} onChange={(e) => setRow(setProjects, projects, i, { description: e.target.value })} /></Field>
          <div className="row-actions">
            <button type="button" className="btn small danger" onClick={() => dropRow(setProjects, projects, i)}>Remove</button>
          </div>
        </div>
      ))}

      {sectionHeader("Education", () => setEducation((rows) => [...rows, { id: "", institution: "", degree: "", field_of_study: "", start_date: "", end_date: "", grade: "" }]))}
      {education.map((ed, i) => (
        <div className="entry-block" key={i}>
          <div className="row-grid">
            <Field label="Institution"><input value={ed.institution} onChange={(e) => setRow(setEducation, education, i, { institution: e.target.value })} /></Field>
            <Field label="Degree"><input value={ed.degree ?? ""} onChange={(e) => setRow(setEducation, education, i, { degree: e.target.value })} /></Field>
            <Field label="Field of study"><input value={ed.field_of_study ?? ""} onChange={(e) => setRow(setEducation, education, i, { field_of_study: e.target.value })} /></Field>
            <Field label="Start date"><input type="date" value={ed.start_date ?? ""} onChange={(e) => setRow(setEducation, education, i, { start_date: e.target.value || null })} /></Field>
            <Field label="End date"><input type="date" value={ed.end_date ?? ""} onChange={(e) => setRow(setEducation, education, i, { end_date: e.target.value || null })} /></Field>
            <Field label="Grade / GPA"><input value={ed.grade ?? ""} onChange={(e) => setRow(setEducation, education, i, { grade: e.target.value })} /></Field>
          </div>
          <div className="row-actions">
            <button type="button" className="btn small danger" onClick={() => dropRow(setEducation, education, i)}>Remove</button>
          </div>
        </div>
      ))}

      {sectionHeader("Certifications", () => setCertifications((rows) => [...rows, { id: "", name: "", issuing_organization: "", issue_date: "", expiration_date: "", credential_url: "" }]))}
      {certifications.map((c, i) => (
        <div className="entry-block" key={i}>
          <div className="row-grid">
            <Field label="Name"><input value={c.name} onChange={(e) => setRow(setCertifications, certifications, i, { name: e.target.value })} /></Field>
            <Field label="Issuing organization"><input value={c.issuing_organization ?? ""} onChange={(e) => setRow(setCertifications, certifications, i, { issuing_organization: e.target.value })} /></Field>
            <Field label="Issue date"><input type="date" value={c.issue_date ?? ""} onChange={(e) => setRow(setCertifications, certifications, i, { issue_date: e.target.value || null })} /></Field>
            <Field label="Expiration date"><input type="date" value={c.expiration_date ?? ""} onChange={(e) => setRow(setCertifications, certifications, i, { expiration_date: e.target.value || null })} /></Field>
            <Field label="Credential URL" grow><input value={c.credential_url ?? ""} onChange={(e) => setRow(setCertifications, certifications, i, { credential_url: e.target.value })} /></Field>
          </div>
          <div className="row-actions">
            <button type="button" className="btn small danger" onClick={() => dropRow(setCertifications, certifications, i)}>Remove</button>
          </div>
        </div>
      ))}
    </div>
  );
}