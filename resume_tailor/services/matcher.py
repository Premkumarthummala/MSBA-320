"""
Scores resume bullets against job description keywords using fuzzy matching
and keyword overlap, then returns ranked bullet indexes.
"""

from rapidfuzz import fuzz


def score_bullet(bullet_text: str, jd: dict) -> float:
    """
    Return a relevance score (0-100) for a single bullet against the JD.
    Higher = more relevant.
    """
    text_lower = bullet_text.lower()
    all_keywords = (
        jd.get("keywords", [])
        + jd.get("required_skills", [])
        + jd.get("preferred_skills", [])
    )

    if not all_keywords:
        return 0.0

    scores = []
    for kw in all_keywords:
        # Direct substring match gets full score
        if kw.lower() in text_lower:
            scores.append(100.0)
        else:
            # Fuzzy partial match for related phrasing
            scores.append(fuzz.partial_ratio(kw.lower(), text_lower))

    if not scores:
        return 0.0

    # Use average of top-3 scores to reward breadth without penalising short bullets
    top_scores = sorted(scores, reverse=True)[:3]
    return sum(top_scores) / len(top_scores)


def rank_bullets(experience: list[dict], jd: dict) -> list[dict]:
    """
    Add a 'relevance_score' to each bullet and sort experience entries' bullets
    by descending score. Returns the mutated experience list.
    """
    for entry in experience:
        for bullet in entry.get("bullets", []):
            bullet["relevance_score"] = score_bullet(bullet["text"], jd)
        entry["bullets"].sort(key=lambda b: b.get("relevance_score", 0), reverse=True)
    return experience


def get_top_bullets(experience: list[dict], top_n: int = 5) -> list[dict]:
    """
    Return the top_n most relevant bullets across all experience entries.
    Used for building the summary rewrite prompt context.
    """
    all_bullets = []
    for entry in experience:
        for bullet in entry.get("bullets", []):
            all_bullets.append({
                "text": bullet["text"],
                "score": bullet.get("relevance_score", 0),
                "company": entry.get("company", ""),
                "title": entry.get("title", ""),
            })
    all_bullets.sort(key=lambda b: b["score"], reverse=True)
    return all_bullets[:top_n]
