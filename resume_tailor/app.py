"""
Resume Tailoring Tool — Streamlit App
Free, local, private. Uses Ollama for AI (no API key needed).
"""

import os
import re
import json
import tempfile
import shutil
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Resume Tailor",
    page_icon="📄",
    layout="wide",
)

# ── local imports ────────────────────────────────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).parent))

from services.resume_parser import parse_resume
from services.jd_parser import parse_jd
from services.matcher import rank_bullets, get_top_bullets
from services.prompt_builder import build_summary_prompt, build_bullets_prompt
from services.ai_rewriter import call_model, extract_json
from services.validator import build_allowed_corpus, validate_summary, validate_bullets
from services.docx_updater import update_docx

# ── helpers ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR = Path(__file__).parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)


def safe_filename(text: str) -> str:
    return re.sub(r"[^\w\s-]", "", text).strip().replace(" ", "_")


def _session(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


# ── sidebar: settings ────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    backend = st.selectbox(
        "AI Backend",
        ["ollama", "groq", "openrouter"],
        index=0,
        help="Ollama is free and runs locally. Groq/OpenRouter require an API key.",
    )

    model_defaults = {
        "ollama": "llama3",
        "groq": "llama3-8b-8192",
        "openrouter": "mistralai/mistral-7b-instruct",
    }
    model = st.text_input("Model", value=model_defaults[backend])

    if backend != "ollama":
        env_key = "GROQ_API_KEY" if backend == "groq" else "OPENROUTER_API_KEY"
        api_key_input = st.text_input(f"{backend.capitalize()} API Key", type="password",
                                      value=os.getenv(env_key, ""))
        if api_key_input:
            os.environ[env_key] = api_key_input

    st.divider()
    st.subheader("Rewrite Options")
    rewrite_summary = st.checkbox("Rewrite Summary", value=True)
    rewrite_bullets = st.checkbox("Rewrite Experience Bullets", value=True)
    conservative_mode = st.checkbox("Conservative Mode", value=True,
                                    help="Only rewrite bullets with relevance score > 40.")
    min_score = st.slider("Min bullet score to rewrite", 0, 100, 40) if conservative_mode else 0

    st.divider()
    if backend == "ollama":
        st.info("Ollama must be running.\n\n```\nollama serve\n```\nand pull a model:\n```\nollama pull llama3\n```")


# ── main area ────────────────────────────────────────────────────────────────
st.title("📄 Resume Tailor")
st.caption("Upload your resume, paste a job description, get a tailored DOCX — free and private.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload Resume")
    uploaded = st.file_uploader("Base resume (.docx)", type=["docx"])

with col2:
    st.subheader("2. Paste Job Description")
    jd_text = st.text_area("Job Description", height=250, placeholder="Paste the full job description here...")


# ── parse resume once uploaded ────────────────────────────────────────────────
if uploaded:
    resume_tmp = TEMP_DIR / "base_resume.docx"
    resume_tmp.write_bytes(uploaded.read())

    if "parsed_resume" not in st.session_state or st.session_state.get("resume_name") != uploaded.name:
        with st.spinner("Parsing resume structure..."):
            st.session_state["parsed_resume"] = parse_resume(str(resume_tmp))
            st.session_state["resume_name"] = uploaded.name
            st.session_state["resume_path"] = str(resume_tmp)

    parsed = st.session_state["parsed_resume"]

    with st.expander("Resume Structure (debug)", expanded=False):
        st.write(f"**Summary paragraphs:** {parsed['summary']['paragraph_indexes']}")
        st.write(f"**Skills:** {', '.join(parsed['skills']['items'][:15])}")
        for exp in parsed["experience"]:
            st.write(f"**{exp['title']} @ {exp['company']}** — {len(exp['bullets'])} bullets")
        st.write(f"**Protected indexes:** {parsed['protected_indexes'][:20]}...")


# ── run tailoring ─────────────────────────────────────────────────────────────
run_disabled = not (uploaded and jd_text.strip())

if st.button("🚀 Tailor Resume", disabled=run_disabled, type="primary"):
    parsed = st.session_state["parsed_resume"]
    resume_path = st.session_state["resume_path"]
    corpus = build_allowed_corpus(parsed)

    progress = st.progress(0, text="Starting...")
    results = {}

    # Step 1: parse JD
    progress.progress(10, text="Parsing job description...")
    try:
        jd = parse_jd(jd_text, model=model)
        st.session_state["jd"] = jd
    except Exception as e:
        st.error(f"JD parsing failed: {e}")
        st.stop()

    # Step 2: rank bullets
    progress.progress(20, text="Scoring resume bullets against JD...")
    experience = rank_bullets(parsed["experience"], jd)
    top_bullets = get_top_bullets(experience, top_n=5)

    # Step 3: rewrite summary
    summary_update = None
    if rewrite_summary and parsed["summary"]["text"]:
        progress.progress(35, text="Rewriting summary...")
        prompt = build_summary_prompt(
            parsed["summary"]["text"],
            parsed["skills"]["items"],
            top_bullets,
            jd_text,
        )
        try:
            raw = call_model(prompt, model=model, backend=backend)
            data = extract_json(raw)
            new_summary = data.get("rewritten_summary", "")
            summary_warnings = validate_summary(new_summary, parsed["summary"]["text"], corpus)
            if summary_warnings:
                st.warning("Summary validation warnings:\n" + "\n".join(f"- {w}" for w in summary_warnings))
            summary_update = {
                "paragraph_indexes": parsed["summary"]["paragraph_indexes"],
                "rewritten_text": new_summary,
            }
            results["summary"] = {"original": parsed["summary"]["text"], "rewritten": new_summary, "warnings": summary_warnings}
        except Exception as e:
            st.warning(f"Summary rewrite failed, keeping original: {e}")

    # Step 4: rewrite bullets
    bullet_updates = []
    bullet_results = []
    if rewrite_bullets:
        total_entries = len([e for e in experience if e["bullets"]])
        for ei, entry in enumerate(experience):
            if not entry["bullets"]:
                continue
            bullets_to_rewrite = [b for b in entry["bullets"] if b.get("relevance_score", 0) >= min_score]
            if not bullets_to_rewrite:
                continue

            pct = 50 + int(40 * ei / max(total_entries, 1))
            progress.progress(pct, text=f"Rewriting bullets for {entry.get('title', 'role')}...")
            prompt = build_bullets_prompt(entry, jd_text)
            try:
                raw = call_model(prompt, model=model, backend=backend)
                data = extract_json(raw)
                rewritten = data.get("rewritten_bullets", [])
                # Align with original bullet count
                orig_texts = [b["text"] for b in entry["bullets"]]
                orig_indexes = [b["paragraph_index"] for b in entry["bullets"]]
                validations = validate_bullets(rewritten, orig_texts, corpus)

                for i, (orig_idx, orig_text) in enumerate(zip(orig_indexes, orig_texts)):
                    if i < len(rewritten) and entry["bullets"][i].get("relevance_score", 0) >= min_score:
                        new_text = rewritten[i]
                        bullet_updates.append({"paragraph_index": orig_idx, "rewritten_text": new_text})
                        bullet_results.append({
                            "company": entry.get("company", ""),
                            "title": entry.get("title", ""),
                            "original": orig_text,
                            "rewritten": new_text,
                            "score": entry["bullets"][i].get("relevance_score", 0),
                            "warnings": validations[i]["warnings"] if i < len(validations) else [],
                        })
            except Exception as e:
                st.warning(f"Bullet rewrite failed for {entry.get('title', 'role')}: {e}")

    results["bullets"] = bullet_results
    st.session_state["results"] = results

    # Step 5: build output DOCX
    progress.progress(92, text="Building tailored DOCX...")
    job_title_safe = safe_filename(jd.get("job_title", "Role")[:30])
    output_filename = f"PremKumar_Resume_{job_title_safe}.docx"
    output_path = str(OUTPUT_DIR / output_filename)
    try:
        update_docx(
            source_path=resume_path,
            output_path=output_path,
            summary_updates=summary_update,
            bullet_updates=bullet_updates if bullet_updates else None,
        )
        st.session_state["output_path"] = output_path
        st.session_state["output_filename"] = output_filename
    except Exception as e:
        st.error(f"DOCX update failed: {e}")
        st.stop()

    progress.progress(100, text="Done!")
    st.success(f"Resume tailored successfully for **{jd.get('job_title', 'the role')}**!")


# ── preview results ───────────────────────────────────────────────────────────
if "results" in st.session_state and "jd" in st.session_state:
    jd = st.session_state["jd"]
    results = st.session_state["results"]

    st.divider()
    st.subheader("Preview")

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Target Role", jd.get("job_title", "—"))
        st.write("**Top Keywords:**", ", ".join(jd.get("keywords", [])[:10]))
    with col_b:
        st.write("**Required Skills:**", ", ".join(jd.get("required_skills", [])[:8]))
        st.write("**Responsibilities:**")
        for r in jd.get("responsibilities", [])[:4]:
            st.write(f"- {r}")

    # Summary preview
    if "summary" in results:
        st.subheader("Summary Rewrite")
        s = results["summary"]
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Original")
            st.info(s["original"])
        with c2:
            st.caption("Rewritten")
            st.success(s["rewritten"])
        if s.get("warnings"):
            st.warning("Warnings: " + "; ".join(s["warnings"]))

    # Bullet previews
    if results.get("bullets"):
        st.subheader("Bullet Rewrites")
        for b in results["bullets"]:
            with st.expander(f"{b['title']} @ {b['company']} — score {b['score']:.0f}"):
                bc1, bc2 = st.columns(2)
                with bc1:
                    st.caption("Original")
                    st.info(b["original"])
                with bc2:
                    st.caption("Rewritten")
                    st.success(b["rewritten"])
                if b.get("warnings"):
                    st.warning("; ".join(b["warnings"]))


# ── download ──────────────────────────────────────────────────────────────────
if "output_path" in st.session_state:
    st.divider()
    st.subheader("Download Tailored Resume")
    output_path = st.session_state["output_path"]
    filename = st.session_state["output_filename"]

    with open(output_path, "rb") as f:
        st.download_button(
            label=f"⬇️ Download {filename}",
            data=f,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
        )
    st.caption("Always review the tailored resume manually before submitting.")
