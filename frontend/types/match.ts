export type MatchCategory = "STRONG_MATCH" | "GOOD_MATCH" | "REVIEW" | "LOW_MATCH";

export interface MatchScores {
  skill: number | null;
  role: number | null;
  experience: number | null;
  project: number | null;
  education: number | null;
  location: number | null;
  semantic: number | null;
}

export interface AlignmentBlock {
  status?: string | null;
  reason?: string | null;
  weight?: number | null;
  required?: string | null;
  candidate_years?: number | null;
  relevant_count?: number | null;
  job_title?: string | null;
  target_role?: string | null;
}

export interface RelevantProject {
  project: string;
  reason: string;
  score: number;
}

export interface MatchResponse {
  id: string;
  job_id: string;
  candidate_profile_id: string;
  overall_score: number;
  category: MatchCategory;
  match_version: string;
  scores: MatchScores;
  matching_skills: string[];
  matching_preferred_skills: string[];
  related_required_matches: string[];
  missing_required_skills: string[];
  role_alignment: AlignmentBlock;
  experience_alignment: AlignmentBlock;
  education_alignment: AlignmentBlock;
  project_alignment: AlignmentBlock;
  location_alignment: AlignmentBlock;
  strengths: string[];
  gaps: string[];
  explanation: string | null;
  relevant_projects: RelevantProject[];
  is_stale: boolean;
  created_at: string;
  updated_at: string;
}

export interface JobMatchListItem {
  id: string;
  job_id: string;
  job_title: string;
  company: string;
  location: string | null;
  work_mode: string | null;
  overall_score: number;
  category: MatchCategory;
  is_stale: boolean;
  matching_skills: string[];
  missing_required_skills: string[];
  role_alignment: AlignmentBlock;
  created_at: string;
}

export interface PaginatedMatches {
  items: JobMatchListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface MatchFilters {
  page?: number;
  page_size?: number;
  sort?: string;
  category?: string;
  score_min?: number;
  score_max?: number;
  location?: string;
  role?: string;
  company?: string;
  stale?: boolean;
}

export const MATCH_CATEGORIES: MatchCategory[] = ["STRONG_MATCH", "GOOD_MATCH", "REVIEW", "LOW_MATCH"];
export const MATCH_SORTS = ["match", "newest", "oldest", "role", "company", "stale"] as const;

export function categoryRank(category: MatchCategory | string | undefined | null): number {
  const index = MATCH_CATEGORIES.indexOf(category as MatchCategory);
  return index === -1 ? MATCH_CATEGORIES.length : index;
}