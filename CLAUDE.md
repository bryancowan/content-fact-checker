# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app locally
streamlit run web_app.py

# Deploy to Render (config in render.yaml)
# Uses: streamlit run web_app.py --server.headless true --server.address 0.0.0.0 --server.port $PORT
```

## Environment Setup

Copy `.env.example` to `.env` and populate both keys:
- `CEREBRAS_API_KEY` — for LLM inference (`qwen-3.8-27b` by default)
- `PARALLEL_API_KEY` — for web search

On Streamlit Cloud, secrets are read via `st.secrets` (takes priority over `.env`). An optional `APP_PASSWORD` secret gates access behind a login screen.

## Architecture

This is a Streamlit web app (`web_app.py`) backed by a library in `src/fact_checker/`.

**Pipeline flow:**
1. User submits text, a URL, or an image via the Streamlit UI
2. `claims.py` extracts atomic factual claims using the Cerebras LLM (URL path: fetches HTML with `requests`/`BeautifulSoup` first; image path: sends the image as a base64 data URI to the vision-capable model)
3. `checker.py` loops over claims; for each one, `search.py` queries Parallel's Search API for web evidence (text-based, regardless of the original input type)
4. `checker.py` calls the Cerebras LLM again to judge the claim against the evidence, returning `true`/`false`/`uncertain` with a reason and sources
5. Results are displayed in the UI and stored in `st.session_state["history"]` for the session sidebar

Cited `top_sources` are filtered against the URLs the search actually returned (`checker.py`), which drops hallucinated citations and any link injected via untrusted input.

**Key modules:**
- `src/fact_checker/config.py` — API keys, model name (`qwen-3.8-27b`), reasoning/token settings, rate limit, retry and image constraints. Most values are overridable via env vars or Streamlit secrets, so a model deprecation doesn't require a code change.
- `src/fact_checker/clients.py` — lazy singleton clients for Cerebras and Parallel APIs
- `src/fact_checker/rate_limiter.py` — sliding-window rate limiter; defaults to the paid tier's 300 req/min (set `CEREBRAS_REQUESTS_PER_MIN=5` on the free trial)
- `src/fact_checker/llm.py` — single `call_cerebras_chat()` function; accepts optional `image_data_urls` for multimodal calls; always acquires rate limiter before calling. Raises `CerebrasCallError` on API failure or empty content rather than degrading silently.
- `src/fact_checker/search.py` — `search_web()` wraps Parallel API; `build_evidence_context()` formats results for the LLM prompt (unaffected by image support — evidence search is always text-based)
- `src/fact_checker/claims.py` — LLM-based claim extraction from text, URL, or image (PNG/JPEG only)
- `src/fact_checker/checker.py` — `fact_check_text()` / `fact_check_url()` / `fact_check_image()` orchestrate the full pipeline; `ClaimResult` dataclass holds verdict/reason/sources

`web_app.py` adds `src/` to `sys.path` and imports directly from `fact_checker`.

## Theming

The app is served at factchecker.bryancowan.com and mirrors the personal site's design
(`personal-website/src/styles/global.css`): the palette and fonts (Newsreader headings,
IBM Plex Sans body) live in `.streamlit/config.toml` under `[theme.light]`/`[theme.dark]`.
Update both repos together. Fonts are self-hosted from `static/fonts/` (served via
`server.enableStaticServing`) rather than Google Fonts, so visitors' browsers never contact
Google; the files and their OFL licenses come from the site's `@fontsource-variable`
packages. The few things the theme config can't express (mint link underline, active tab
color) are in the `st.html` style block at the top of `web_app.py`.

Streamlit always renders primary-button text in white, so the dark theme's `primaryColor`
is a deep mint rather than the site's light pill. Streamlit also doesn't expose the active
theme to CSS, so the dark link underline follows `prefers-color-scheme` (the default
"System" setting) and not a manual theme override.

## Testing

`pytest` covers `url_guard.py` (SSRF guard), `rate_limiter.py` (sliding-window behavior), `llm.py` (message/content-block construction), `claims.py` and `checker.py` (structured-output JSON parsing and pipeline orchestration), and `search.py` (Parallel API call shape and evidence formatting). All of it runs offline — `tests/conftest.py` stubs the Cerebras/Parallel SDK modules, and individual tests monkeypatch `call_cerebras_chat`/`search_web`/the client getters rather than hitting the network.

## Model Notes

`qwen-3.8-27b` reasons by default at `reasoning_effort="high"`, and reasoning tokens
count against the completion budget — hence `DEFAULT_MAX_COMPLETION_TOKENS = 16384`
rather than the 4096 used with the previous, non-reasoning model. `reasoning_format`
is pinned to `"parsed"` so the reasoning trace lands in `message.reasoning` and
`message.content` stays pure JSON for the structured-output parsers.

Use `max_completion_tokens`, not the deprecated `max_tokens`; sending both is an error.

Image input is untrusted: `claims.py`'s vision system prompt explicitly instructs the
model to treat image text as data, never instructions.

## CI

`.github/workflows/ci.yml` runs `ruff check .` and `pytest -q` on push to `main` and on
every PR. The suite is offline and needs no secrets.

## Debugging third-party API failures

**Check the provider status pages before investigating anything else:**

- Parallel (web search) — https://status.parallel.ai
- Cerebras (inference) — https://status.cerebras.ai

Provider incidents can surface as errors that point at the wrong thing. A Parallel outage
can return `401 {"code":16,"message":"No API key provided (C.0)"}` for requests that carry
a valid `x-api-key`, which reads as a credential bug. Example:
`docs/incidents/2026-09-07-parallel-search-401.md`.

Two things that make this class of bug hard to see:

- The unit tests are fully offline (`tests/conftest.py` stubs both SDKs), so they pass
  green during a total provider outage. Only live calls confirm the pipeline works.
- `config.py` reads secrets and `clients.py` caches clients **at import time**, so a
  process restart is required after changing a key.
