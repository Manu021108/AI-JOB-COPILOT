import { getToken } from "./auth";
import type { TokenResponse, User } from "@/types/auth";
const API_URL = process.env.NEXT_PUBLIC_API_URL;
if (!API_URL) console.warn("NEXT_PUBLIC_API_URL is not configured.");
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try { response = await fetch(`${API_URL}${path}`, { ...options, headers: { "Content-Type": "application/json", ...options.headers } }); }
  catch { throw new Error("Unable to connect to server."); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Something went wrong.");
  return body as T;
}
export const registerUser = (data: {name:string;email:string;password:string}) => request<{message:string}>("/api/auth/register", {method:"POST",body:JSON.stringify(data)});
export const loginUser = (data: {email:string;password:string}) => request<TokenResponse>("/api/auth/login", {method:"POST",body:JSON.stringify(data)});
export const getCurrentUser = () => request<User>("/api/users/me", {headers:{Authorization:`Bearer ${getToken()}`}});
export const healthCheck = () => request<{status:string;database:string}>("/api/health");
