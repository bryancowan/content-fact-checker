import re

_UNESCAPED_DOLLAR = re.compile(r"(?<!\\)\$")


def escape_dollars(text: str) -> str:
    """Escape ``$`` so Streamlit's markdown renderer prints it literally.

    Streamlit treats ``$...$`` as inline LaTeX, so a claim like "priced at $5
    per million input tokens and $25 per million output tokens" loses both
    dollar signs and renders the text between them as math. Fact-checked content
    is full of prices, so every model- or user-supplied string that reaches
    ``st.markdown`` goes through this first.

    Already-escaped dollars are left alone, so applying it twice is a no-op.
    """
    return _UNESCAPED_DOLLAR.sub(r"\\$", text)
