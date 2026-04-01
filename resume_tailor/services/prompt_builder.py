"""
Builds strict prompts for summary and bullet rewriting.
"""


SUMMARY_PROMPT = """\
You are helping tailor a resume for a job application.

Rewrite the professional summary so it aligns with the target job description.

Rules:
- Use ONLY information already present in the candidate's resume
- Do NOT invent skills, tools, certifications, employers, titles, or years
- Keep it professional, concise, and ATS-friendly
- Emphasize keywords from the job description ONLY if supported by the resume
- Keep it approximately the same length as the original summary (within 20%)
- Return ONLY valid JSON, no commentary

Resume summary:
{summary_text}

Relevant resume skills:
{skills_list}

Relevant experience highlights:
{experience_highlights}

Job description:
{job_description}

Return JSON:
{{
  "rewritten_summary": "..."
}}
"""


BULLETS_PROMPT = """\
You are tailoring a resume to a target job description.

Rewrite the experience bullets to better match the job description.

Rules:
- Use ONLY facts from the original bullets
- Do NOT invent tools, achievements, projects, or metrics
- Do NOT change company names, job titles, or dates
- Keep the SAME number of bullets
- Keep each rewritten bullet similar in length to the original (within 20%)
- Make the language stronger, clearer, and more aligned with the job description
- Preserve truthfulness above all
- Return ONLY valid JSON, no commentary

Job description:
{job_description}

Experience section:
Company: {company}
Title: {title}
Dates: {dates}

Original bullets:
{numbered_bullets}

Return JSON:
{{
  "rewritten_bullets": ["...", "...", "..."]
}}
"""


def build_summary_prompt(summary_text: str, skills: list[str], top_bullets: list[dict], job_description: str) -> str:
    experience_highlights = "\n".join(
        f"- {b['text']}" for b in top_bullets[:5]
    )
    skills_list = ", ".join(skills[:20]) if skills else "See resume"
    return SUMMARY_PROMPT.format(
        summary_text=summary_text,
        skills_list=skills_list,
        experience_highlights=experience_highlights,
        job_description=job_description,
    )


def build_bullets_prompt(entry: dict, job_description: str) -> str:
    bullets = entry.get("bullets", [])
    numbered = "\n".join(f"{i+1}. {b['text']}" for i, b in enumerate(bullets))
    return BULLETS_PROMPT.format(
        job_description=job_description,
        company=entry.get("company", ""),
        title=entry.get("title", ""),
        dates=entry.get("dates", ""),
        numbered_bullets=numbered,
    )
