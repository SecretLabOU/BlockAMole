"""doctext.py -- stdlib-only conversion of saved HTML/Markdown/PDF to text.

Used by analysis.py to turn raw/ documentation snapshots into plain-text
snapshots (derived/doc_text/) and to check that every quoted fact appears
verbatim in its source.
"""

import html
import re
import shutil
import subprocess
from html.parser import HTMLParser

_BLOCK = {"p", "div", "br", "li", "ul", "ol", "tr", "table", "section",
          "article", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote",
          "dt", "dd", "dl", "header", "footer", "main", "nav", "aside",
          "figure", "figcaption", "summary", "details", "hr", "thead",
          "tbody"}
_CELL = {"td", "th"}
_SKIP = {"script", "style", "noscript", "svg", "template", "head"}


class _P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip += 1
        elif tag in _BLOCK:
            self.out.append("\n")
        elif tag in _CELL:
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in _BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(raw_bytes):
    s = raw_bytes.decode("utf-8", errors="replace")
    p = _P()
    p.feed(s)
    p.close()
    t = html.unescape("".join(p.out))
    t = t.replace(" ", " ").replace(" ", " ")
    lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in t.split("\n")]
    out, blank = [], 0
    for ln in lines:
        if ln:
            out.append(ln)
            blank = 0
        else:
            blank += 1
            if blank == 1:
                out.append("")
    return "\n".join(out).strip() + "\n"


def pdf_to_text(path, layout=False):
    """Reading-order text (layout=False) keeps sentences contiguous for
    quote checks; layout=True keeps table rows on one line for parsing."""
    if shutil.which("pdftotext") is None:
        raise RuntimeError("pdftotext (poppler-utils) is required for PDFs")
    cmd = ["pdftotext"] + (["-layout"] if layout else []) + [path, "-"]
    r = subprocess.run(cmd, capture_output=True, check=True)
    return r.stdout.decode("utf-8", errors="replace")


def file_to_text(path, layout=False):
    low = path.lower()
    if low.endswith(".pdf"):
        return pdf_to_text(path, layout=layout)
    with open(path, "rb") as f:
        b = f.read()
    if low.endswith((".html", ".htm")):
        return html_to_text(b)
    return b.decode("utf-8", errors="replace")


def norm(s):
    """Whitespace- and quote-insensitive normal form for verbatim checks."""
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip().lower()
