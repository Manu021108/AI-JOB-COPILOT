from __future__ import annotations

# Explicit, conservative relationships between skills. These only capture
# skills that are genuinely interchangeable in a job context. Deliberately
# NOT included: Python=Django, AWS=Azure, React=Angular, Java=JavaScript.
# Extend this map with care.
_RELATED: dict[str, set[str]] = {}


def _related(*names: str) -> None:
    for name in names:
        _RELATED.setdefault(name.lower(), set()).update(other.lower() for other in names if other != name)


_related("PostgreSQL", "SQL")
_related("MySQL", "SQL")
_related("SQLite", "SQL")
_related("Python", "FastAPI")
_related("JavaScript", "TypeScript")
_related("JavaScript", "Node.js")
_related("JavaScript", "React")
_related("React", "Next.js")
_related("Node.js", "Express")
_related("Deep Learning", "Machine Learning")
_related("PyTorch", "Deep Learning")
_related("TensorFlow", "Deep Learning")
_related("scikit-learn", "Machine Learning")
_related("NLP", "RAG")
_related("LLM", "RAG")
_related("RAG", "LangChain")
_related("TensorFlow", "PyTorch")


def related_skills(name: str) -> set[str]:
    """Set of normalized skills considered related to the given skill."""
    return _RELATED.get(name.lower().strip(), set())