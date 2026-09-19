"use client";
import type { MatchCategory } from "@/types/match";

export const CATEGORY_COLORS: Record<string, string> = {
  STRONG_MATCH: "#18794e",
  GOOD_MATCH: "#1a5aae",
  REVIEW: "#b45309",
  LOW_MATCH: "#b42318",
};

export const CATEGORY_LABELS: Record<string, string> = {
  STRONG_MATCH: "Strong match",
  GOOD_MATCH: "Good match",
  REVIEW: "Worth a review",
  LOW_MATCH: "Low match",
};

export default function MatchScoreRing({
  score,
  category,
  size = 72,
  showLabel = true,
}: {
  score: number;
  category: MatchCategory | string;
  size?: number;
  showLabel?: boolean;
}) {
  const pct = Math.round(Math.max(0, Math.min(100, score)));
  const color = CATEGORY_COLORS[category] ?? "#8a97ac";
  return (
    <div className="match-ring-wrap" style={{ width: size, height: size }}>
      <div className="match-ring match-ring-big" style={{ background: `conic-gradient(${color} ${pct * 3.6}deg, #e6eaf4 0deg)` }}>
        <div className="match-ring-inner">
          <strong>{pct}</strong>
          {showLabel && <span className="match-ring-label">{CATEGORY_LABELS[category] ?? category}</span>}
        </div>
      </div>
    </div>
  );
}