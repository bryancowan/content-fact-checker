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
- `CEREBRAS_API_KEY` — for LLM inference (gemma-4-31b model)
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

**Key modules:**
- `src/fact_checker/config.py` — API keys, model name (`gemma-4-31b`), rate limit constant, image size/mime-type constraints
- `src/fact_checker/clients.py` — lazy singleton clients for Cerebras and Parallel APIs
- `src/fact_checker/rate_limiter.py` — sliding-window rate limiter enforcing 5 req/min on Cerebras free tier
- `src/fact_checker/llm.py` — single `call_cerebras_chat()` function; accepts optional `image_data_urls` for multimodal calls; always acquires rate limiter before calling
- `src/fact_checker/search.py` — `search_web()` wraps Parallel API; `build_evidence_context()` formats results for the LLM prompt (unaffected by image support — evidence search is always text-based)
- `src/fact_checker/claims.py` — LLM-based claim extraction from text, URL, or image (PNG/JPEG only)
- `src/fact_checker/checker.py` — `fact_check_text()` / `fact_check_url()` / `fact_check_image()` orchestrate the full pipeline; `ClaimResult` dataclass holds verdict/reason/sources

`web_app.py` adds `src/` to `sys.path` and imports directly from `fact_checker`. There are no tests.
