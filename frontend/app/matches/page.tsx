"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import ProtectedRoute from "@/components/ProtectedRoute";
import Sidebar from "@/components/Sidebar";
import MatchesList from "@/components/matches/MatchesList";
import { clearToken } from "@/lib/auth";
import { getCurrentUser, getProfile, recalculateMatches } from "@/lib/api";
import type { User } from "@/types/auth";

export default function MatchesPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [hasProfile, setHasProfile] = useState(true);
  const [recalcBusy, setRecalcBusy] = useState(false);
  const [recalculated, setRecalculated] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    getCurrentUser().then(setUser).catch(() => { clearToken(); router.replace("/login"); });
    getProfile().then(() => setHasProfile(true)).catch(() => setHasProfile(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  const handleRecalculate = async () => {
    if (recalcBusy) return;
    setRecalcBusy(true);
    setNotice(null);
    try {
      const result = await recalculateMatches();
      setRecalculated(result.recalculated);
      setNotice(`Recalculated ${result.recalculated} existing match${result.recalculated === 1 ? "" : "es"}.`);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setRecalcBusy(false);
    }
  };

  if (!user) return <ProtectedRoute><></></ProtectedRoute>;

  return (
    <ProtectedRoute>
      <main className="dashboard">
        <Sidebar />
        <section className="content">
          <Navbar name={user.name} />
          <div className="page-head">
            <h1 style={{ marginTop: 24 }}>Job Matches</h1>
            <p className="muted">How well each job lines up with your profile.</p>
          </div>
          {!hasProfile && (
            <div className="banner">
              Upload and analyze your resume first — matches are calculated against your candidate profile.
            </div>
          )}
          {notice && <div className="banner">{notice}</div>}
          <div className="job-detail-actions" style={{ marginTop: 14 }}>
            <button className="btn secondary" onClick={handleRecalculate} disabled={recalcBusy}>
              {recalcBusy ? "Recalculating…" : "Recalculate all matches"}
            </button>
          </div>
          <div style={{ marginTop: 10 }}>
            <MatchesList key={recalculated} />
          </div>
        </section>
      </main>
    </ProtectedRoute>
  );
}