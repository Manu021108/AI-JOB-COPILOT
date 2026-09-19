export type JobStatus = "ACTIVE" | "CLOSED" | "EXPIRED" | "ARCHIVED";
export type JobSource = "USER_SUBMITTED" | "URL";

export interface JobItem {
  id: string;
  title: string;
  company: string;
  location: string | null;
  source: JobSource;
  status: JobStatus;
  work_mode: string | null;
  employment_type: string | null;
  created_at: string;
  has_analysis: boolean;
}

export interface Job extends JobItem {
  source_url: string | null;
  source_job_id: string | null;
  experience_min: number | null;
  experience_max: number | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  description: string | null;
  application_url: string | null;
  posted_at: string | null;
  updated_at: string;
}

export interface JobInput {
  title?: string;
  company?: string;
  location?: string | null;
  description?: string | null;
  application_url?: string | null;
  source_url?: string | null;
  employment_type?: string | null;
  work_mode?: string | null;
  experience_min?: number | null;
  experience_max?: number | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  status?: JobStatus;
}

export interface JobDescriptionInput {
  title?: string;
  company?: string;
  location?: string | null;
  description: string;
  application_url?: string | null;
  source_url?: string | null;
}

export interface JobAnalysis {
  job_id: string;
  summary: string | null;
  required_skills: string[];
  preferred_skills: string[];
  responsibilities: string[];
  qualifications: string[];
  education_requirements: string[];
  experience_requirements: string[];
  tools_and_technologies: string[];
  nice_to_have: string[];
  employment_details: string | null;
  updated_at: string;
}

export interface PaginatedJobs {
  items: JobItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface JobFilters {
  page?: number;
  page_size?: number;
  search?: string;
  company?: string;
  location?: string;
  source?: string;
  status?: string;
  work_mode?: string;
  sort?: string;
}

export const JOB_STATUSES: JobStatus[] = ["ACTIVE", "CLOSED", "EXPIRED", "ARCHIVED"];
export const WORK_MODES = ["", "Remote", "Hybrid", "Onsite", "On-site"];
export const EMPLOYMENT_TYPES = ["", "Full Time", "Part Time", "Contract", "Internship", "Freelance"];