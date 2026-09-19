"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import ProtectedRoute from "@/components/ProtectedRoute";
import Sidebar from "@/components/Sidebar";
import AddJobModal from "@/components/jobs/AddJobModal";
import JobsList from "@/components/jobs/JobsList";
import { clearToken } from "@/lib/auth";
import { getCurrentUser, listJobs } from "@/lib/api";
import type { Job, JobFilters, JobItem } from "@/types/job";
import type { User } from "@/types/auth";

export default function JobsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [items, setItems] = useState<JobItem[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<JobFilters>({ page: 1, page_size: 12, sort: "newest" });
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);

  const load = async (nextFilters: JobFilters) => {
    setLoading(true);
    setPageError(null);
    try {
      const data = await listJobs(nextFilters);
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setPageError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getCurrentUser().then(setUser).catch(() => { clearToken(); router.replace("/login"); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  useEffect(() => {
    load(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  if (!user) return <ProtectedRoute><></></ProtectedRoute>;

  return (
    <ProtectedRoute>
      <main className="dashboard">
        <Sidebar />
        <section className="content">
          <Navbar name={user.name} />
          <div className="page-head">
            <h1 style={{ marginTop: 28 }}>Job Intelligence</h1>
            <p className="muted">Track roles you're interested in — add them manually, by URL, or from a pasted description.</p>
          </div>
          {pageError && <div className="error banner">{pageError}</div>}

          <div style={{ marginTop: 20 }}>
            <JobsList
              items={items}
              total={total}
              filters={filters}
              loading={loading}
              onFiltersChange={setFilters}
              onAdd={() => setModalOpen(true)}
            />
          </div>
        </section>
      </main>
      {modalOpen && (
        <AddJobModal
          onClose={() => setModalOpen(false)}
          onCreated={(job: Job) => {
            setModalOpen(false);
            router.push(`/jobs/${job.id}`);
          }}
        />
      )}
    </ProtectedRoute>
  );
}