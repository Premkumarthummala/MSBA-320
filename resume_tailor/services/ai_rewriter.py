"""
Sends prompts to the configured AI backend and returns raw text responses.
Supports Ollama (local, free) as primary and Groq/OpenRouter as optional fallbacks.
"""

import json
import re
import os
import requests


def call_model(prompt: str, model: str = "llama3", backend: str = "ollama") -> str:
    """
    Send a prompt to the selected backend and return the raw text response.
    backend: "ollama" | "groq" | "openrouter"
    """
    if backend == "ollama":
        return _call_ollama(prompt, model)
    elif backend == "groq":
        return _call_groq(prompt, model)
    elif backend == "openrouter":
        return _call_openrouter(prompt, model)
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _call_ollama(prompt: str, model: str) -> str:
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3},
    }
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure Ollama is running: run `ollama serve` in a terminal."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama request timed out. Try a smaller model like mistral.")


def _call_groq(prompt: str, model: str) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment or .env file.")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model or "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_openrouter(prompt: str, model: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment or .env file.")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "resume-tailor-local",
    }
    payload = {
        "model": model or "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def extract_json(raw: str) -> dict:
    """Extract the first JSON object from a raw model response."""
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError(f"No JSON found in model response:\n{raw[:300]}")
    return json.loads(match.group())
