"""
Extracts structured signals from a job description text using the local AI model.
Falls back to simple keyword extraction if AI is unavailable.
"""

import json
import re
from services.ai_rewriter import call_model


JD_PARSE_PROMPT = """\
Extract the most important hiring signals from this job description.

Return ONLY valid JSON with this exact structure:
{{
  "job_title": "...",
  "keywords": ["keyword1", "keyword2"],
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill1"],
  "responsibilities": ["responsibility1", "responsibility2"]
}}

Rules:
- keywords: tools, technologies, domain terms repeated or emphasized
- required_skills: explicitly listed as required/must-have
- preferred_skills: listed as preferred/nice-to-have
- responsibilities: 3-6 core duties, each a short phrase
- Do not add commentary outside the JSON

Job Description:
{job_description}
"""


def parse_jd(job_description: str, model: str = "llama3") -> dict:
    """
    Parse a job description into structured signals.
    Returns a dict with job_title, keywords, required_skills, preferred_skills, responsibilities.
    """
    prompt = JD_PARSE_PROMPT.format(job_description=job_description)
    raw = call_model(prompt, model=model)

    try:
        # Extract JSON block if model wrapped it in markdown
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            data = json.loads(match.group())
            # Normalise keys
            return {
                "job_title": data.get("job_title", ""),
                "keywords": [k.strip() for k in data.get("keywords", [])],
                "required_skills": [k.strip() for k in data.get("required_skills", [])],
                "preferred_skills": [k.strip() for k in data.get("preferred_skills", [])],
                "responsibilities": [r.strip() for r in data.get("responsibilities", [])],
            }
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: basic keyword extraction without AI
    return _fallback_parse(job_description)


def _fallback_parse(text: str) -> dict:
    """Simple regex-based fallback when AI is unavailable."""
    words = re.findall(r"\b[A-Z][a-zA-Z0-9+#./-]{2,}\b", text)
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    keywords = [w for w, c in sorted(freq.items(), key=lambda x: -x[1]) if c > 1][:15]

    # Guess job title from first line
    first_line = text.strip().split("\n")[0][:80]

    return {
        "job_title": first_line,
        "keywords": keywords,
        "required_skills": [],
        "preferred_skills": [],
        "responsibilities": [],
    }
