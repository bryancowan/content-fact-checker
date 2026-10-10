import re

# A "$" preceded by an even number of backslashes (including none), which
# Markdown reads as pairs of literal backslashes and so leaves the "$" live.
# Group 1 keeps those backslashes. An odd count means the "$" is already escaped.
_UNESCAPED_DOLLAR = re.compile(r"(?<!\\)((?:\\\\)*)\$")


def escape_dollars(text: str) -> str:
    """Escape ``$`` so Streamlit's markdown renderer prints it literally.

    Streamlit treats ``$...$`` as inline LaTeX, so a claim like "priced at $5
    per million input tokens and $25 per million output tokens" loses both
    dollar signs and renders the text between them as math. Fact-checked content
    is full of prices, so every model- or user-supplied string that reaches
    ``st.markdown`` goes through this first.

    A dollar already escaped by an odd number of backslashes is left alone, so
    applying it twice is a no-op. Paired backslashes (``\\\\$``) don't escape
    anything in Markdown, so those dollars are still escaped.
    """
    return _UNESCAPED_DOLLAR.sub(r"\1\\$", text)
