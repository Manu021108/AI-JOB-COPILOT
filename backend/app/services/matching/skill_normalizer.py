from __future__ import annotations

from app.services.skill_categorizer import normalize_skill_name as _categorizer_normalize

# Additional canonical-name aliases on top of the shared skill categorizer.
# Extend this map to normalize more job-posting spellings of the same skill.
_EXTRA_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "jsx": "React",
    "ts": "TypeScript",
    "react js": "React",
    "react.js": "React",
    "reactjs": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "sqlserver": "SQL Server",
    "sqldb": "SQL",
    "rest": "REST API",
    "api": "REST API",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "llms": "LLM",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "postgres": "PostgreSQL",
    "psql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "react native": "React Native",
    "reactnative": "React Native",
    "typescript": "TypeScript",
    "next js": "Next.js",
    "nextjs": "Next.js",
    "express js": "Express",
    "expressjs": "Express",
    "golang": "Go",
    "cpp": "C++",
    "c#": "C#",
    ".net": "ASP.NET",
    "aspnet": "ASP.NET",
    "bash": "Bash",
    "shell": "Shell",
    "power shell": "PowerShell",
    "ci cd": "CI/CD",
    "cicd": "CI/CD",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "terraform": "Terraform",
    "grafana": "Grafana",
    "prometheus": "Prometheus",
}

_EXTRA_ALIASES_LOWER = {key.lower().strip(): value for key, value in _EXTRA_ALIASES.items()}


def normalize_skill(name: str) -> str:
    """Canonical skill name for matching. Falls back to the shared categorizer."""
    raw = _categorizer_normalize(name or "")
    key = raw.lower().strip()
    canonical = _EXTRA_ALIASES_LOWER.get(key)
    return canonical or raw