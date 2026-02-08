import textwrap
from .clients import get_parallel_client


def search_web(query: str, num: int = 5, mode: str = "one-shot") -> list[dict]:
    """Search the web using Parallel's Search API.

    Returns a list of dicts with: url, title, publish_date, excerpts.
    """
    objective = (
        f"Find high-quality, up-to-date sources that answer the question:\n\n{query}\n\n"
        "Prefer authoritative sites (e.g., .gov, .edu, major news, or official org websites)."
    )

    search = get_parallel_client().beta.search(
        objective=objective,
        search_queries=[query],
        mode=mode,
        max_results=num,
        excerpts={"max_chars_per_result": 8000},
    )

    results = []
    for r in search.results:
        results.append({
            "url": r.url,
            "title": getattr(r, "title", None),
            "publish_date": getattr(r, "publish_date", None),
            "excerpts": list(r.excerpts or []),
        })
    return results


def build_evidence_context(results: list[dict], max_chars: int = 8000) -> str:
    """Format search results into a readable evidence block for the LLM."""
    blocks = []
    for idx, r in enumerate(results):
        excerpts_text = "\n\n".join(r["excerpts"][:2])
        block = textwrap.dedent(f"""
        [Source {idx + 1}]
        Title: {r['title'] or r['url']}
        URL: {r['url']}
        Publish date: {r['publish_date']}

        Excerpts:
        {excerpts_text}
        """).strip()
        blocks.append(block)

    context = "\n\n".join(blocks)
    if len(context) > max_chars:
        context = context[:max_chars] + "\n\n[Context truncated for length]"
    return context
