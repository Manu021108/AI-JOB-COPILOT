export interface ResumeItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  version: number;
  is_active: boolean;
  has_profile: boolean;
  created_at: string;
}

export interface ResumeUploadResponse {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  version: number;
  is_active: boolean;
  status: "uploaded";
  profile_created: boolean;
}

export interface Skill {
  id: string;
  skill_name: string;
  skill_category: string;
  proficiency?: string | null;
}

export interface Experience {
  id: string;
  company: string;
  job_title: string;
  location?: string | null;
  employment_type?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  description?: string | null;
  is_current?: boolean;
}

export interface Project {
  id: string;
  project_name: string;
  description?: string | null;
  technologies: string[];
  project_url?: string | null;
  start_date?: string | null;
  end_date?: string | null;
}

export interface Education {
  id: string;
  institution: string;
  degree?: string | null;
  field_of_study?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  grade?: string | null;
}

export interface Certification {
  id: string;
  name: string;
  issuing_organization?: string | null;
  issue_date?: string | null;
  expiration_date?: string | null;
  credential_url?: string | null;
}

export interface CandidateProfile {
  id: string;
  resume_id?: string | null;
  full_name?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  linkedin_url?: string | null;
  github_url?: string | null;
  portfolio_url?: string | null;
  professional_summary?: string | null;
  target_roles: string[];
  years_of_experience?: number | null;
  skills: Skill[];
  experience: Experience[];
  projects: Project[];
  education: Education[];
  certifications: Certification[];
  updated_at: string;
}

export interface Completeness {
  percentage: number;
  missing: string[];
}