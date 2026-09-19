"""Configuration for the hybrid job matching engine.

Everything that tunes how matches are scored and categorized lives here so it
can be adjusted independently of the matcher logic. When the algorithm changes
in a backward-incompatible way, bump MATCH_VERSION.
"""
from __future__ import annotations

# Version of the matching algorithm. Stored on every match row; when this
# changes all stored matches are invalidated and need recalculation.
MATCH_VERSION = "v1"

# Default weights for the weighted scoring aggregator. Must sum to ~1.0;
# they are renormalized defensively at load time should they drift.
MATCH_WEIGHTS: dict[str, float] = {
    "skills": 0.40,
    "role": 0.20,
    "experience": 0.15,
    "projects": 0.10,
    "education": 0.05,
    "location": 0.05,
    "semantic": 0.05,
}


def normalized_weights() -> dict[str, float]:
    total = sum(MATCH_WEIGHTS.values()) or 1.0
    return {key: value / total for key, value in MATCH_WEIGHTS.items()}


# Match categories used by the workflow, not a hiring judgment.
# STRONG_MATCH: 85-100  GOOD_MATCH: 70-84  REVIEW: 55-69  LOW_MATCH: 0-54
MATCH_CATEGORIES = [
    ("STRONG_MATCH", 85.0),
    ("GOOD_MATCH", 70.0),
    ("REVIEW", 55.0),
    ("LOW_MATCH", 0.0),
]


def category_for_score(score: float) -> str:
    for name, floor in MATCH_CATEGORIES:
        if score >= floor:
            return name
    return "LOW_MATCH"


# Credit granted for a related (not exact) skill hit. Missing required skills
# hurt more than missing nice-to-have ones; preferred skills only add a small
# bonus on top of the required match.
REQUIRED_RELATED_CREDIT = 0.6
PREFERRED_RELATED_CREDIT = 0.5
PREFERRED_BONUS_SPAN = 20.0

# Minimum relevance score for a project to be surfaced as relevant.
PROJECT_MIN_RELEVANCE = 40.0
PROJECT_MAX_SURFACED = 5

# Experience scoring knobs.
EXPERIENCE_OVER_QUALIFICATION_PENALTY = 8.0
EXPERIENCE_ONLY_MAX_PENALTY = 10.0

# Semantic matching is skipped when either side has fewer than this many chars.
SEMANTIC_MIN_TEXT_CHARS = 20