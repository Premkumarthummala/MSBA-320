"""
Validates rewritten content against the original resume to detect hallucinations.
Flags new tools, certifications, employers, and suspicious new metrics.
"""

import re


# Common tech/tool pattern — words with capitals, dots, plus signs, numbers
TECH_PATTERN = re.compile(r"\b[A-Z][a-zA-Z0-9+#./]{1,}\b")
METRIC_PATTERN = re.compile(r"\b\d+[\%xX]?\b|\b\d+\s*(percent|times|x|hours|days|years|months)\b", re.IGNORECASE)


def _extract_tokens(text: str) -> set[str]:
    return set(re.findall(r"\b\w[\w+#./]*\b", text.lower()))


def _extract_tech_terms(text: str) -> set[str]:
    return set(m.lower() for m in TECH_PATTERN.findall(text))


def _extract_metrics(text: str) -> list[str]:
    return METRIC_PATTERN.findall(text)


def build_allowed_corpus(parsed_resume: dict) -> str:
    """Combine all original resume text into one searchable corpus."""
    parts = [parsed_resume.get("summary", {}).get("text", "")]
    parts += parsed_resume.get("skills", {}).get("items", [])
    for entry in parsed_resume.get("experience", []):
        parts.append(entry.get("company", ""))
        parts.append(entry.get("title", ""))
        parts.append(entry.get("dates", ""))
        for bullet in entry.get("bullets", []):
            parts.append(bullet.get("text", ""))
    return " ".join(parts)


def validate_text(rewritten: str, original: str, corpus: str) -> list[str]:
    """
    Compare rewritten text against original and full corpus.
    Returns a list of warning strings (empty = passed).
    """
    warnings = []
    corpus_tokens = _extract_tokens(corpus)
    original_tokens = _extract_tokens(original)

    # Check for new tech terms not in the full corpus
    rewritten_tech = _extract_tech_terms(rewritten)
    for term in rewritten_tech:
        if term not in corpus_tokens and len(term) > 3:
            warnings.append(f"Possible hallucination: '{term}' not found in your resume.")

    # Check for new metrics not in the original bullet/summary
    original_metrics = set(m.lower() for m in _extract_metrics(original))
    rewritten_metrics = set(m.lower() for m in _extract_metrics(rewritten))
    new_metrics = rewritten_metrics - original_metrics
    for m in new_metrics:
        warnings.append(f"New metric added: '{m}' — not in original text.")

    return warnings


def validate_bullets(rewritten_bullets: list[str], original_bullets: list[str], corpus: str) -> list[dict]:
    """
    Validate each rewritten bullet against its original.
    Returns list of {index, warnings} dicts.
    """
    results = []
    for i, (rewritten, original) in enumerate(zip(rewritten_bullets, original_bullets)):
        warnings = validate_text(rewritten, original, corpus)
        results.append({"index": i, "warnings": warnings})
    return results


def validate_summary(rewritten_summary: str, original_summary: str, corpus: str) -> list[str]:
    return validate_text(rewritten_summary, original_summary, corpus)
