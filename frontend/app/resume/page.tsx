"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import ProtectedRoute from "@/components/ProtectedRoute";
import Sidebar from "@/components/Sidebar";
import UploadResume from "@/components/resume/UploadResume";
import ResumeCard from "@/components/resume/ResumeCard";
import ProfileCompleteness from "@/components/resume/ProfileCompleteness";
import ProfileView from "@/components/resume/ProfileView";
import ProfileEditor from "@/components/resume/ProfileEditor";
import { clearToken } from "@/lib/auth";
import { deleteResume, getCurrentUser, getProfile, getProfileCompleteness, listResumes, updateProfile } from "@/lib/api";
import type { CandidateProfile, Completeness, ResumeItem } from "@/types/resume";
import type { User } from "@/types/auth";

export default function ResumePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [resumes, setResumes] = useState<ResumeItem[] | null>(null);
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [completeness, setCompleteness] = useState<Completeness | null>(null);
  const [editing, setEditing] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refreshResumes = async () => {
    try { setResumes(await listResumes()); } catch (e) { setPageError((e as Error).message); }
  };

  const refreshProfile = async () => {
    try {
      const [p, c] = await Promise.all([getProfile(), getProfileCompleteness()]);
      setProfile(p);
      setCompleteness(c);
    } catch (e) {
      const status = (e as Error).message;
      setProfile(null);
      setCompleteness(null);
      if (!status.toLowerCase().includes("profile")) setPageError(status);
    }
  };

  useEffect(() => {
    getCurrentUser().then(setUser).catch(() => { clearToken(); router.replace("/login"); });
    refreshResumes();
    refreshProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  const handleUploaded = () => {
    refreshResumes();
    refreshProfile();
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Delete this resume? The candidate profile built from it will also be removed.")) return;
    setBusy(true);
    try {
      await deleteResume(id);
      await refreshResumes();
      await refreshProfile();
    } catch (e) {
      setPageError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async (payload: unknown) => {
    await updateProfile(payload as Partial<CandidateProfile>);
    setEditing(false);
    await refreshProfile();
  };

  if (!user) return <ProtectedRoute><></></ProtectedRoute>;

  return (
    <ProtectedRoute>
      <main className="dashboard">
        <Sidebar />
        <section className="content">
          <Navbar name={user.name} />
          <div className="page-head">
            <h1 style={{ marginTop: 28 }}>Resume Intelligence</h1>
            <p className="muted">Upload your resume once — we build and maintain your structured candidate profile.</p>
          </div>
          {pageError && <div className="error banner">{pageError}</div>}

          <div className="resume-grid">
            <div className="col">
              <UploadResume onUploaded={handleUploaded} />
              <ResumeCard resumes={resumes ?? []} onDeleted={handleDelete} />
            </div>
            <div className="col">
              {completeness && <ProfileCompleteness percentage={completeness.percentage} missing={completeness.missing} />}
            </div>
          </div>

          {busy && <div className="muted" style={{ marginTop: 12 }}>Working…</div>}

          <div style={{ marginTop: 28 }}>
            {profile ? (
              editing ? (
                <ProfileEditor profile={profile} onSave={handleSave} onCancel={() => setEditing(false)} />
              ) : (
                <ProfileView profile={profile} onEdit={() => setEditing(true)} />
              )
            ) : (
              <div className="card empty-state">
                <h3>No candidate profile yet</h3>
                <p className="muted">Upload a resume and we will build your candidate profile from it automatically.</p>
              </div>
            )}
          </div>
        </section>
      </main>
    </ProtectedRoute>
  );
}