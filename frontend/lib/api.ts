import { getToken } from "./auth";
import type {
  CandidateProfile,
  Completeness,
  ResumeItem,
  ResumeUploadResponse,
} from "@/types/resume";
import type { Job, JobAnalysis, JobDescriptionInput, JobInput, JobFilters, PaginatedJobs } from "@/types/job";
import type { TokenResponse, User } from "@/types/auth";
import type { JobMatchListItem, MatchFilters, MatchResponse, PaginatedMatches } from "@/types/match";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
if (!process.env.NEXT_PUBLIC_API_URL) console.warn("NEXT_PUBLIC_API_URL is not configured; defaulting to http://localhost:8000.");

class ApiError extends Error {
  code?: string;
  constructor(message: string, code?: string) {
    super(message);
    this.code = code;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try { response = await fetch(`${API_URL}${path}`, { ...options, headers: { "Content-Type": "application/json", ...options.headers } }); }
  catch { throw new Error("Unable to connect to server."); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Something went wrong.");
  return body as T;
}

async function requestEnvelope<T>(path: string, options: RequestInit = {}, hasToken = false): Promise<T> {
  let response: Response;
  const headers: Record<string, string> = { ...(options.headers as Record<string, string> | undefined) };
  if (!hasToken) headers["Content-Type"] = "application/json";
  if (getToken()) headers["Authorization"] = `Bearer ${getToken()}`;
  try { response = await fetch(`${API_URL}${path}`, { ...options, headers }); }
  catch { throw new ApiError("Unable to connect to server."); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = (body as any)?.detail;
    const error = detail?.error;
    throw new ApiError(error?.message || detail || "Something went wrong.", error?.code);
  }
  return (body as any)?.data as T;
}

export const registerUser = (data: { name: string; email: string; password: string }) =>
  request<{ message: string }>("/api/auth/register", { method: "POST", body: JSON.stringify(data) });
export const loginUser = (data: { email: string; password: string }) =>
  request<TokenResponse>("/api/auth/login", { method: "POST", body: JSON.stringify(data) });
export const getCurrentUser = () => request<User>("/api/users/me", { headers: { Authorization: `Bearer ${getToken()}` } });
export const healthCheck = () => request<{ status: string; database: string }>("/api/health");

export const uploadResume = (file: File, onProgress?: (phase: string) => void) => {
  const fd = new FormData();
  fd.append("file", file);
  onProgress?.("uploading");
  return requestEnvelope<ResumeUploadResponse>(`/api/resumes/upload`, { method: "POST", body: fd }, true);
};
export const listResumes = () => requestEnvelope<ResumeItem[]>("/api/resumes");
export const deleteResume = (id: string) => requestEnvelope<{ id: string }>(`/api/resumes/${id}`, { method: "DELETE" });

export const getProfile = () => requestEnvelope<CandidateProfile>("/api/profile");
export const updateProfile = (payload: Partial<CandidateProfile>) =>
  requestEnvelope<CandidateProfile>("/api/profile", { method: "PUT", body: JSON.stringify(payload) });
export const getProfileCompleteness = () => requestEnvelope<Completeness>("/api/profile/completeness");

export const listJobs = (filters: JobFilters = {}) =>
  requestEnvelope<PaginatedJobs>(`/api/jobs?${buildJobQuery(filters)}`);
export const getJob = (id: string) => requestEnvelope<Job>(`/api/jobs/${id}`);
export const createJob = (payload: JobInput) =>
  requestEnvelope<Job>("/api/jobs", { method: "POST", body: JSON.stringify(payload) });
export const createJobFromDescription = (payload: JobDescriptionInput) =>
  requestEnvelope<Job>("/api/jobs/from-description", { method: "POST", body: JSON.stringify(payload) });
export const importJobFromUrl = (url: string) =>
  requestEnvelope<Job>("/api/jobs/import-url", { method: "POST", body: JSON.stringify({ url }) });
export const updateJob = (id: string, payload: JobInput) =>
  requestEnvelope<Job>(`/api/jobs/${id}`, { method: "PUT", body: JSON.stringify(payload) });
export const deleteJob = (id: string) =>
  requestEnvelope<{ id: string }>(`/api/jobs/${id}`, { method: "DELETE" });
export const analyzeJob = (id: string) =>
  requestEnvelope<JobAnalysis>(`/api/jobs/${id}/analyze`, { method: "POST" });
export const getJobAnalysis = (id: string) => requestEnvelope<JobAnalysis>(`/api/jobs/${id}/analysis`);

export const calculateJobMatch = (jobId: string) =>
  requestEnvelope<MatchResponse>(`/api/jobs/${jobId}/match`, { method: "POST" });
export const getJobMatch = (jobId: string) => requestEnvelope<MatchResponse>(`/api/jobs/${jobId}/match`);
export const listMatches = (filters: MatchFilters = {}) =>
  requestEnvelope<PaginatedMatches>(`/api/matches?${buildMatchQuery(filters)}`);
export const getMatch = (matchId: string) => requestEnvelope<MatchResponse>(`/api/matches/${matchId}`);
export const recalculateMatches = () => requestEnvelope<{ recalculated: number; items: JobMatchListItem[] }>("/api/matches/recalculate", { method: "POST" });
export const runAllMatches = () => requestEnvelope<{ generated: number; items: JobMatchListItem[] }>("/api/matches/run", { method: "POST" });

function buildJobQuery(filters: JobFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  });
  return params.toString();
}

function buildMatchQuery(filters: MatchFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  });
  return params.toString();
}