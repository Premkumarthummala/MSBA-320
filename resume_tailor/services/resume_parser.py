"""
Reads a DOCX resume and identifies paragraph indexes for summary, skills,
experience bullets, and protected sections.
"""

from docx import Document
from docx.oxml.ns import qn
import re


SECTION_ALIASES = {
    "summary": ["summary", "professional summary", "profile", "about me", "objective"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "tools"],
    "experience": ["experience", "professional experience", "work experience", "employment", "work history"],
    "education": ["education", "academic background", "academics", "qualifications"],
    "certifications": ["certifications", "certificates", "licenses"],
    "projects": ["projects", "key projects"],
}

PROTECTED_SECTIONS = {"education", "certifications", "projects"}


def _is_bullet(para) -> bool:
    """Return True if paragraph is a bullet point (real Word bullet or dash/symbol prefix)."""
    # Check for Word numbering (bullet list)
    if para.paragraph_format.element.find(qn("w:numPr")) is not None:
        return True
    text = para.text.strip()
    if text and text[0] in ("•", "–", "—", "-", "▪", "◦", "○", "●", "◆", "*"):
        return True
    return False


def _is_section_heading(text: str) -> str | None:
    """Return section key if text matches a known section heading, else None."""
    normalized = text.strip().lower()
    for section, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            if normalized == alias or normalized == alias.upper() or normalized.startswith(alias):
                return section
    return None


def _looks_like_role_header(text: str) -> bool:
    """Heuristic: role header lines are short and contain dates or a pipe separator."""
    if len(text) < 5:
        return False
    date_pattern = r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4}|present|current)\b"
    if re.search(date_pattern, text, re.IGNORECASE):
        return True
    if "|" in text or "–" in text or "—" in text:
        return True
    return False


def parse_resume(docx_path: str) -> dict:
    """
    Parse a DOCX resume and return a structured dict with paragraph indexes.

    Returns:
        {
            "paragraphs": [{"index": int, "text": str, "style": str, "is_bullet": bool}],
            "summary": {"text": str, "paragraph_indexes": [int]},
            "skills": {"items": [str], "paragraph_indexes": [int]},
            "experience": [
                {
                    "company": str,
                    "title": str,
                    "dates": str,
                    "header_indexes": [int],
                    "bullets": [{"text": str, "paragraph_index": int}]
                }
            ],
            "protected_indexes": [int]   # indexes never to rewrite
        }
    """
    doc = Document(docx_path)
    paragraphs_raw = []

    for i, para in enumerate(doc.paragraphs):
        paragraphs_raw.append({
            "index": i,
            "text": para.text,
            "style": para.style.name if para.style else "",
            "is_bullet": _is_bullet(para),
        })

    result = {
        "paragraphs": paragraphs_raw,
        "summary": {"text": "", "paragraph_indexes": []},
        "skills": {"items": [], "paragraph_indexes": []},
        "experience": [],
        "protected_indexes": [],
    }

    current_section = None
    current_exp_entry = None
    protected_indexes = []

    for p in paragraphs_raw:
        text = p["text"].strip()
        idx = p["index"]

        if not text:
            continue

        section = _is_section_heading(text)
        if section:
            current_section = section
            if section in PROTECTED_SECTIONS:
                protected_indexes.append(idx)
            # Save any open experience entry
            if current_exp_entry and section == "experience":
                pass  # starting fresh experience section
            continue

        # Always protect if in a protected section
        if current_section in PROTECTED_SECTIONS:
            protected_indexes.append(idx)
            continue

        if current_section == "summary":
            if result["summary"]["text"]:
                result["summary"]["text"] += " " + text
            else:
                result["summary"]["text"] = text
            result["summary"]["paragraph_indexes"].append(idx)

        elif current_section == "skills":
            result["skills"]["paragraph_indexes"].append(idx)
            # Parse comma or pipe separated skills
            for skill in re.split(r"[,|•\n]", text):
                s = skill.strip()
                if s:
                    result["skills"]["items"].append(s)

        elif current_section == "experience":
            if _is_bullet(doc.paragraphs[idx]):
                if current_exp_entry is None:
                    # No header seen yet — create a placeholder
                    current_exp_entry = {"company": "", "title": "", "dates": "", "header_indexes": [], "bullets": []}
                    result["experience"].append(current_exp_entry)
                current_exp_entry["bullets"].append({"text": text, "paragraph_index": idx})
            elif _looks_like_role_header(text):
                protected_indexes.append(idx)
                # Try to parse company/title/dates from the line
                current_exp_entry = {"company": "", "title": "", "dates": "", "header_indexes": [idx], "bullets": []}
                result["experience"].append(current_exp_entry)
                # Simple parse: "Title | Company | Dates" or "Company – Title (Dates)"
                parts = re.split(r"\s*[\|│]\s*", text)
                if len(parts) >= 2:
                    current_exp_entry["title"] = parts[0].strip()
                    current_exp_entry["company"] = parts[1].strip()
                    if len(parts) >= 3:
                        current_exp_entry["dates"] = parts[2].strip()
                else:
                    current_exp_entry["company"] = text
            else:
                # Could be a second header line (e.g., company name on separate line)
                protected_indexes.append(idx)
                if current_exp_entry:
                    current_exp_entry["header_indexes"].append(idx)
                    if not current_exp_entry["company"]:
                        current_exp_entry["company"] = text

    result["protected_indexes"] = list(set(protected_indexes))
    return result


def print_paragraphs(docx_path: str):
    """Debug helper: print all paragraph indexes and text."""
    doc = Document(docx_path)
    for i, para in enumerate(doc.paragraphs):
        bullet = " [BULLET]" if _is_bullet(para) else ""
        print(f"[{i:3d}] style={para.style.name:<30} {bullet} | {para.text[:80]}")
