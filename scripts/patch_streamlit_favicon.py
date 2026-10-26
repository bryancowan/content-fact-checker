"""Point Streamlit's own HTML at this app's favicon.

Streamlit serves index.html with a hardcoded <link rel="shortcut icon" href="./favicon.png">
(its crown logo). st.set_page_config(page_icon=...) only swaps that link after the page connects
over the websocket, so some browsers, link previews and crawlers keep the crown. This rewrites the
link in the installed package, and overwrites the bundled favicon.png for anything that probes it.

Run after `pip install` (render.yaml does). Safe to re-run. Exits 1 if Streamlit's index.html no
longer has the link we expect, so an upgrade that moves it fails the build instead of quietly
bringing the crown back.
"""

import importlib.util
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICON = ROOT / "static" / "favicon-magnifier.png"
ORIGINAL_LINK = '<link rel="shortcut icon" href="./favicon.png" />'
PATCHED_LINK = '<link rel="shortcut icon" href="/app/static/favicon-magnifier.png" />'


def patch(streamlit_static: Path, icon: Path = ICON) -> str:
    """Patch a Streamlit static dir. Returns "patched" or "already patched"; raises ValueError."""
    index = streamlit_static / "index.html"
    html = index.read_text(encoding="utf-8")
    if PATCHED_LINK in html:
        status = "already patched"
    elif ORIGINAL_LINK in html:
        index.write_text(html.replace(ORIGINAL_LINK, PATCHED_LINK, 1), encoding="utf-8")
        status = "patched"
    else:
        raise ValueError(f"{index} has neither the original nor the patched favicon link")
    shutil.copyfile(icon, streamlit_static / "favicon.png")
    return status


def main() -> int:
    spec = importlib.util.find_spec("streamlit")
    if spec is None or spec.origin is None:
        print("streamlit is not installed", file=sys.stderr)
        return 1
    static = Path(spec.origin).parent / "static"
    try:
        print(f"{static}: {patch(static)}")
    except (OSError, ValueError) as err:
        print(f"Could not patch Streamlit's favicon: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
