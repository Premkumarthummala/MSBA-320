# Resume Tailor

A free, private, local tool that rewrites your resume to match a job description while preserving your original DOCX formatting.

## Quick Start

### 1. Install dependencies

```bash
cd resume_tailor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Ollama (free local AI)

Download from https://ollama.com then pull a model:

```bash
ollama pull llama3
# or a smaller/faster option:
ollama pull qwen2.5
```

Start Ollama before running the app:

```bash
ollama serve
```

### 3. Run the app

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## How it works

1. Upload your base resume (.docx)
2. Paste a job description
3. Click **Tailor Resume**
4. Review the preview (original vs rewritten)
5. Download the tailored .docx

## What gets rewritten

| Section | Behaviour |
|---|---|
| Professional Summary | Rewritten to emphasise JD-relevant skills you already have |
| Experience Bullets | Rephrased to match JD language — no new facts added |
| Company names, titles, dates | Never touched |
| Education, certifications | Never touched |

## Optional: Cloud AI backends

If local generation feels slow, add an API key to a `.env` file:

```
GROQ_API_KEY=your_key_here
# or
OPENROUTER_API_KEY=your_key_here
```

Then switch the backend in the sidebar. Groq offers a generous free tier.

## Folder structure

```
resume_tailor/
├── app.py                  # Streamlit UI
├── requirements.txt
├── input/                  # Put your base resume here
├── output/                 # Tailored resumes saved here
├── temp/                   # Temporary working files
└── services/
    ├── resume_parser.py    # DOCX structure detection
    ├── jd_parser.py        # Job description extraction
    ├── matcher.py          # Bullet relevance scoring
    ├── prompt_builder.py   # Strict AI prompts
    ├── ai_rewriter.py      # Ollama / Groq / OpenRouter calls
    ├── validator.py        # Hallucination detection
    └── docx_updater.py     # Safe paragraph replacement
```
