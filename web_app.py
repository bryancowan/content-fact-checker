"""Content Fact-Checker — Streamlit Web Interface"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st
from fact_checker import fact_check_text, fact_check_url, ClaimResult


st.set_page_config(page_title="Content Fact-Checker", page_icon="🔍", layout="wide")


def _check_password() -> bool:
    """Gate the app behind a shared password stored in st.secrets."""
    try:
        correct_pw = st.secrets["APP_PASSWORD"]
    except (KeyError, FileNotFoundError):
        return True  # No password configured — allow access (local dev)

    if st.session_state.get("authenticated"):
        return True

    st.title("Content Fact-Checker")
    pw = st.text_input("Enter the access password:", type="password")
    if st.button("Submit", type="primary"):
        if pw == correct_pw:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    return False


if not _check_password():
    st.stop()

if "history" not in st.session_state:
    st.session_state["history"] = []

st.title("Content Fact-Checker")
st.markdown(
    "Extract claims from text or URLs, retrieve real-world evidence, "
    "and evaluate each claim as **True**, **False**, or **Uncertain**."
)

VERDICT_STYLES = {
    "true": {"emoji": "✅", "color": "#28a745"},
    "false": {"emoji": "❌", "color": "#dc3545"},
    "uncertain": {"emoji": "⚠️", "color": "#ffc107"},
}

tab_text, tab_url = st.tabs(["Check Text", "Check URL"])

with tab_text:
    text_input = st.text_area(
        "Paste the text you want to fact-check:",
        height=200,
        placeholder="e.g., The Earth is flat and the moon is made of cheese. Albert Einstein was born in Germany in 1879.",
    )
    text_submit = st.button("Fact-Check Text", type="primary", key="text_btn")

with tab_url:
    url_input = st.text_input(
        "Enter a URL to fact-check:",
        placeholder="https://www.example.com/article",
    )
    url_submit = st.button("Fact-Check URL", type="primary", key="url_btn")


_GREEN_BAR_HTML = (
    '<div style="width:100%;background:#333;border-radius:4px;overflow:hidden">'
    '<div style="width:100%;height:8px;background:#28a745;border-radius:4px"></div>'
    "</div>"
)


def display_results(results: list[ClaimResult]):
    st.markdown("---")
    st.subheader(f"Results: {len(results)} claims checked")

    for i, r in enumerate(results, 1):
        style = VERDICT_STYLES.get(r.verdict, VERDICT_STYLES["uncertain"])
        verdict_display = f"{style['emoji']} **{r.verdict.upper()}**"

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Claim {i}:** {r.claim}")
            with col2:
                st.markdown(verdict_display)

            st.markdown(f"*{r.reason}*")

            if r.sources:
                with st.expander("View sources"):
                    for s in r.sources:
                        st.markdown(f"- {s}")
            st.markdown("---")


if text_submit and text_input.strip():
    with st.status("Fact-checking text...", expanded=True) as status:
        progress_bar = st.progress(0)
        progress_text = st.empty()

        def on_text_progress(message: str, current: int, total: int):
            progress_bar.progress((current + 1) / total)
            progress_text.text(message)

        results = fact_check_text(text_input, on_progress=on_text_progress)
        progress_bar.markdown(_GREEN_BAR_HTML, unsafe_allow_html=True)
        status.update(label="Fact-check complete!", state="complete")

    if results:
        st.session_state["history"].append({
            "timestamp": datetime.now().strftime("%I:%M %p"),
            "input_type": "text",
            "input_preview": text_input[:80],
            "results": results,
        })
        display_results(results)
    else:
        st.warning("No factual claims could be extracted from this text.")

elif text_submit:
    st.warning("Please enter some text to fact-check.")

if url_submit and url_input.strip():
    with st.status("Fetching URL and fact-checking...", expanded=True) as status:
        progress_bar = st.progress(0)
        progress_text = st.empty()

        def on_url_progress(message: str, current: int, total: int):
            progress_bar.progress((current + 1) / total)
            progress_text.text(message)

        results = fact_check_url(url_input, on_progress=on_url_progress)
        progress_bar.markdown(_GREEN_BAR_HTML, unsafe_allow_html=True)
        status.update(label="Fact-check complete!", state="complete")

    if results:
        st.session_state["history"].append({
            "timestamp": datetime.now().strftime("%I:%M %p"),
            "input_type": "url",
            "input_preview": url_input,
            "results": results,
        })
        display_results(results)
    else:
        st.warning("No factual claims could be extracted from this URL.")

elif url_submit:
    st.warning("Please enter a URL to fact-check.")

# --- Sidebar: Session History ---
with st.sidebar:
    st.header("Session History")
    history = st.session_state["history"]

    if not history:
        st.caption("No fact-checks yet this session.")
    else:
        for entry in reversed(history):
            verdicts = [r.verdict for r in entry["results"]]
            counts = {v: verdicts.count(v) for v in set(verdicts)}
            summary_parts = [f"{n} {v.capitalize()}" for v, n in counts.items()]
            summary = ", ".join(summary_parts)

            label = f"{entry['timestamp']} — {summary}"
            with st.expander(label):
                kind = "Text" if entry["input_type"] == "text" else "URL"
                preview = entry["input_preview"]
                st.caption(f"**{kind}:** {preview}")
                for i, r in enumerate(entry["results"], 1):
                    style = VERDICT_STYLES.get(r.verdict, VERDICT_STYLES["uncertain"])
                    st.markdown(
                        f"{style['emoji']} **{r.verdict.upper()}** — {r.claim}"
                    )
                    st.markdown(f"*{r.reason}*")

        if st.button("Clear History"):
            st.session_state["history"] = []
            st.rerun()
