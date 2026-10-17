from .clients import get_parallel_client


def search_web(query: str, num: int = 5, mode: str = "fast") -> list[dict]:
    """Search the web using Parallel's Search API.

    Returns a list of dicts with: url, title, publish_date, excerpts.
    """
    objective = (
        f"Find high-quality, up-to-date sources that answer the question:\n\n{query}\n\n"
        "Prefer authoritative sites (e.g., .gov, .edu, major news, or official org websites)."
    )

    search = get_parallel_client().search(
        objective=objective,
        search_queries=[query],
        mode=mode,
        advanced_settings={
            "max_results": num,
            "excerpt_settings": {"max_chars_per_result": 8000},
        },
    )

    results = []
    for r in search.results:
        results.append(
            {
                "url": r.url,
                "title": getattr(r, "title", None),
                "publish_date": getattr(r, "publish_date", None),
                "excerpts": list(r.excerpts or []),
            }
        )
    return results


def _format_source(idx: int, r: dict, excerpts_text: str) -> str:
    return "\n".join(
        [
            f"[Source {idx + 1}]",
            f"Title: {r['title'] or r['url']}",
            f"URL: {r['url']}",
            f"Publish date: {r['publish_date']}",
            "",
            "Excerpts:",
            excerpts_text,
        ]
    )


def _allocate(lengths: list[int], budget: int) -> list[int]:
    """Split budget across sources: short ones keep everything, the rest share what's left."""
    alloc = [0] * len(lengths)
    remaining = max(budget, 0)
    for k, i in enumerate(sorted(range(len(lengths)), key=lengths.__getitem__)):
        alloc[i] = min(lengths[i], remaining // (len(lengths) - k))
        remaining -= alloc[i]
    return alloc


def build_evidence_context(results: list[dict], max_chars: int = 16000) -> str:
    """Format search results into a readable evidence block for the LLM.

    The budget (after headers) is shared across sources: a short excerpt keeps all
    of its text and its unused share goes to the longer ones, so no single source
    can push the others out of the context.
    """
    separator = "\n\n"
    ellipsis = " [...]"
    fixed_chars = sum(len(_format_source(i, r, "")) for i, r in enumerate(results))
    fixed_chars += len(separator) * max(len(results) - 1, 0)

    texts = ["\n\n".join(r["excerpts"][:2]) for r in results]
    alloc = _allocate([len(t) for t in texts], max_chars - fixed_chars)

    blocks = []
    for idx, (r, text) in enumerate(zip(results, texts, strict=True)):
        if len(text) > alloc[idx]:
            text = text[: max(alloc[idx] - len(ellipsis), 0)] + ellipsis
        blocks.append(_format_source(idx, r, text))

    context = separator.join(blocks)
    if len(context) > max_chars:
        context = context[:max_chars] + "\n\n[Context truncated for length]"
    return context
