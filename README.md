# Content Fact-Checker

Extracts claims from any text or URL, retrieves real-world evidence using web search, and evaluates each claim as **True**, **False**, or **Uncertain**.

Powered by the [zai-glm-4.7](https://inference-docs.cerebras.ai/) model on [Cerebras](https://cerebras.ai/) and [Parallel Search](https://parallel.ai/).

Based on the [OpenAI Cookbook: Build Your Own Content Fact-Checker](https://cookbook.openai.com/articles/gpt-oss/build-your-own-fact-checker-cerebras), adapted to use zai-glm-4.7 instead of gpt-oss-120B.

## How It Works

1. **Extract claims** — The LLM breaks input text into atomic, checkable factual statements
2. **Search for evidence** — Each claim is searched against the web using Parallel Search
3. **Judge each claim** — The LLM evaluates evidence and returns a verdict: True, False, or Uncertain, with reasoning and source URLs

## Setup

### Prerequisites

- Python 3.10+
- A [Cerebras API key](https://cloud.cerebras.ai/) (free tier available)
- A [Parallel API key](https://platform.parallel.ai/) (free tier available)

### Installation

```bash
git clone https://github.com/bryancowan/content-fact-checker.git
cd content-fact-checker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` and add your keys:

```
CEREBRAS_API_KEY=your_cerebras_key_here
PARALLEL_API_KEY=your_parallel_key_here
```

## Usage

Activate the virtual environment first:

```bash
source .venv/bin/activate
```

### Web Interface

```bash
streamlit run web_app.py --server.headless true
```

Then open **http://127.0.0.1:8501** in your browser.

> **Safari users:** If you get an HTTPS error with `localhost`, use `http://127.0.0.1:8501` instead.

### CLI

**Check text:**

```bash
python cli.py --text "The Eiffel Tower is located in Berlin."
```

**Check a URL:**

```bash
python cli.py --url "https://www.snopes.com/fact-check/some-article/"
```

**Interactive mode:**

```bash
python cli.py
```

Type text or paste a URL at the `>` prompt. Type `quit` to exit.

## Project Structure

```
content-fact-checker/
├── src/fact_checker/       # Core library (shared by CLI and web)
│   ├── config.py           # API keys, model settings
│   ├── clients.py          # Cerebras + Parallel client init
│   ├── llm.py              # LLM call wrapper (zai-glm-4.7)
│   ├── search.py           # Web search via Parallel
│   ├── claims.py           # Claim extraction from text/URL
│   ├── checker.py          # Fact-check pipeline
│   └── rate_limiter.py     # Free tier rate limiting
├── cli.py                  # Command-line interface
├── web_app.py              # Streamlit web interface
├── requirements.txt        # Python dependencies
└── .env.example            # API key template
```

## Free Tier Limits

- **Cerebras**: 10 requests/min, 1M tokens/day
- A typical fact-check with 6 claims uses 7 API calls, which fits within one minute
- The app automatically pauses and resumes if you hit the rate limit

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Activate the venv: `source .venv/bin/activate` |
| Safari HTTPS error | Use `http://127.0.0.1:8501` instead of `localhost` |
| Rate limit pauses | Normal on the free tier (10 req/min). The app waits and resumes automatically |
| "API key not set" error | Check that `.env` exists with both keys filled in |
