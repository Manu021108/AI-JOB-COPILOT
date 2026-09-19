SKILL_CATEGORIES: dict[str, list[str]] = {
    "Programming": ["Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#", "Go", "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "Shell", "Bash", "PowerShell", "SQL", "R", "Perl", "MATLAB"],
    "Backend": ["FastAPI", "Django", "Flask", "Node.js", "Express", "Spring Boot", "ASP.NET", "Laravel", "Ruby on Rails", "GraphQL", "gRPC", "REST API", "REST", "Celery", "RabbitMQ", "Kafka", "Nginx", "Prometheus", "Grafana"],
    "Frontend": ["React", "Next.js", "Vue", "Angular", "Svelte", "HTML", "CSS", "Tailwind CSS", "Bootstrap", "Redux", "jQuery", "Webpack", "Vite"],
    "Database": ["PostgreSQL", "MySQL", "MongoDB", "SQLite", "Redis", "DynamoDB", "Oracle", "Cassandra", "Elasticsearch", "NoSQL", "Supabase", "Firebase"],
    "AI/ML": ["Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "NLP", "Natural Language Processing", "LLM", "Large Language Models", "RAG", "OpenCV", "scikit-learn", "Keras", "NumPy", "Pandas", "Matplotlib", "LangChain", "Hugging Face", "Transformers", "Computer Vision", "Data Science", "Generative AI"],
    "DevOps": ["Docker", "Kubernetes", "Git", "GitHub", "GitLab", "CI/CD", "Jenkins", "Linux", "AWS", "Azure", "GCP", "Google Cloud", "Terraform", "Ansible", "ArgoCD", "Helm"],
}

_ALIASES: dict[str, str] = {
    "JavaScript": "JavaScript",
    "Typescript": "TypeScript",
    "Nodejs": "Node.js",
    "Node": "Node.js",
    "Nextjs": "Next.js",
    "Next": "Next.js",
    "Expressjs": "Express",
    "Machinelearning": "Machine Learning",
    "Deeplearning": "Deep Learning",
    "Nlp": "NLP",
    "Rag": "RAG",
    "Rag System": "RAG",
    "Postgres": "PostgreSQL",
    "PostgreSql": "PostgreSQL",
}
_ALIASES = {k.lower().strip(): v for k, v in _ALIASES.items()}
_CATEGORY_LOOKUP: dict[str, str] = {}
for _category, _skills in SKILL_CATEGORIES.items():
    for _skill in _skills:
        _CATEGORY_LOOKUP[_skill.lower().strip()] = _category


def normalize_skill_name(name: str) -> str:
    key = name.strip()
    canonical = _ALIASES.get(key.lower())
    if canonical:
        return canonical
    return key or ""


def categorize_skill(name: str) -> str:
    key = name.strip().lower()
    return _CATEGORY_LOOKUP.get(key, "Other")


def categorize_skills(names: list[str]) -> list[tuple[str, str]]:
    """Return a deduplicated list of (category, canonical_name) pairs."""
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for name in names:
        canonical = normalize_skill_name(name)
        if not canonical:
            continue
        key = canonical.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append((categorize_skill(canonical), canonical))
    return result