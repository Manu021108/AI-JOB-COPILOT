import { getToken } from "./auth";
import type {
  CandidateProfile,
  Completeness,
  ResumeItem,
  ResumeUploadResponse,
} from "@/types/resume";
import type { TokenResponse, User } from "@/types/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL;
if (!API_URL) console.warn("NEXT_PUBLIC_API_URL is not configured.");

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