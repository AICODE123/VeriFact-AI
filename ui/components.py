"""
components.py
==============
Reusable Streamlit UI building blocks for VeriFact AI: the verdict/output
card, confidence visualization, evidence + sources display, history list
items, and PDF report export.

Keeping these out of app.py keeps the main app file focused on page layout
and state management rather than widget-level rendering details.
"""

from __future__ import annotations

import io
from typing import List

import streamlit as st

from models.schemas import HistoryEntry, VerdictLabel, VerificationResult

_VERDICT_STYLE = {
    VerdictLabel.SUPPORTED: {"color": "#1a7f37", "icon": "✅", "bg": "#e6f4ea"},
    VerdictLabel.CONTRADICTED: {"color": "#c9302c", "icon": "❌", "bg": "#fbe9e7"},
    VerdictLabel.INSUFFICIENT_EVIDENCE: {"color": "#8a6d00", "icon": "⚠️", "bg": "#fff8e1"},
}

def _sanitize_for_pdf(text: str) -> str:
    """Core Helvetica font only supports cp1252; replace anything outside it."""
    return text.encode("cp1252", errors="replace").decode("cp1252")


def render_verdict_card(result: VerificationResult) -> None:
    
    style = _VERDICT_STYLE[result.verdict]
    offline_note = " · Answered from offline knowledge base" if result.used_offline_kb else ""

    html = (
        f'<div style="border-left: 6px solid {style["color"]}; '
        f'background-color: {style["bg"]}; padding: 1.1rem 1.3rem; '
        f'border-radius: 0.5rem; margin-bottom: 1rem;">'
        f'<div style="font-size: 1.25rem; font-weight: 700; color: {style["color"]};">'
        f'{style["icon"]} {result.verdict.value}</div>'
        f'<div style="font-size: 0.95rem; color: #444; margin-top: 0.3rem;">'
        f'Confidence: <strong>{result.confidence_percent()}</strong>{offline_note}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    st.markdown("#### Reason")
    st.write(result.reason)

    if result.evidence_chunks:
        st.markdown("#### Evidence")
        for chunk in result.evidence_chunks:
            with st.container(border=True):
                st.write(f'"{chunk.text}"')
                st.caption(f"Source: {chunk.source_title}  ·  Relevance: {chunk.similarity_score:.0%}")

    if result.sources:
        st.markdown("#### Sources")
        for src in result.sources:
            st.markdown(f"- [{src}]({src})")

    _render_copy_button(result)


def render_confidence_bar(confidence: float, color: str) -> None:
    """Render a simple horizontal confidence bar visualization."""
    percent = max(0, min(100, round(confidence * 100)))
    st.markdown(
        f"""
        <div style="background-color:#eee; border-radius: 6px; height: 10px; width: 100%; margin: 0.4rem 0 1rem 0;">
            <div style="background-color:{color}; width:{percent}%; height:100%; border-radius: 6px;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_copy_button(result: VerificationResult) -> None:
    """Render a text area + note so the user can easily copy the result summary."""
    summary = build_plaintext_summary(result)
    with st.expander("📋 Copy result as text"):
        st.text_area("Result summary", value=summary, height=180, label_visibility="collapsed")


def build_plaintext_summary(result: VerificationResult) -> str:
    """Build a plain-text summary of a VerificationResult (for copy / export)."""
    lines = [
        f"Claim: {result.claim}",
        f"Decision: {result.verdict.value}",
        f"Confidence: {result.confidence_percent()}",
        "",
        f"Reason: {result.reason}",
    ]
    if result.sources:
        lines.append("")
        lines.append("Sources:")
        lines.extend(f"- {s}" for s in result.sources)
    return "\n".join(lines)


def render_history_list(entries: List[HistoryEntry]) -> None:
    """Render the query history as a list of expandable rows."""
    if not entries:
        st.info("No verification history yet. Verify a claim to see it appear here.")
        return

    for entry in entries:
        style = _VERDICT_STYLE.get(VerdictLabel(entry.verdict), _VERDICT_STYLE[VerdictLabel.INSUFFICIENT_EVIDENCE])
        with st.expander(f"{style['icon']} {entry.claim}  —  {entry.verdict} ({entry.confidence:.0%})"):
            st.caption(entry.timestamp)
            st.write(entry.reason)
            if entry.sources:
                st.markdown("**Sources:** " + entry.sources)


def export_result_to_pdf(result: VerificationResult) -> bytes:
    """
    Build a simple one-page PDF report for a VerificationResult.

    Returns:
        Raw PDF bytes, suitable for `st.download_button`.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Common "smart" Unicode punctuation that cp1252 will happily encode
    # (so a naive encode/decode round-trip won't catch it) but that the
    # built-in "helvetica" core font has no glyph for, causing
    # FPDFUnicodeEncodingException at render time rather than at sanitize
    # time. Map these to plain ASCII explicitly, first.
    _UNICODE_REPLACEMENTS = {
    # Spaces
    "\u00A0": " ",      # Non-breaking space
    "\u2002": " ",      # En space
    "\u2003": " ",      # Em space
    "\u2009": " ",      # Thin space
    "\u202F": " ",      # Narrow no-break space
    "\u200B": "",       # Zero-width space
    "\u2060": "",       # Word joiner

    # Quotes
    "\u2018": "'",      # Left single quote
    "\u2019": "'",      # Right single quote / apostrophe
    "\u201A": "'",      # Single low-9 quote
    "\u201B": "'",      # Reversed single quote

    "\u201C": '"',      # Left double quote
    "\u201D": '"',      # Right double quote
    "\u201E": '"',      # Double low-9 quote

    # Dashes / Hyphens
    "\u2010": "-",      # Hyphen
    "\u2011": "-",      # Non-breaking hyphen
    "\u2012": "-",      # Figure dash
    "\u2013": "-",      # En dash
    "\u2014": "--",     # Em dash
    "\u2212": "-",      # Minus sign

    # Ellipsis
    "\u2026": "...",

    # Bullets
    "\u2022": "-",      # Bullet
    "\u25CF": "-",      # Black circle
    "\u25E6": "-",      # White bullet

    # Symbols
    "\u00D7": "x",      # Multiplication sign
    "\u2713": "[OK]",   # ✓
    "\u2714": "[OK]",   # ✔
    "\u2717": "[X]",    # ✗
    "\u2718": "[X]",    # ✘

    # Arrows
    "\u2190": "<-",
    "\u2192": "->",
    "\u2191": "^",
    "\u2193": "v",
    "\u21D2": "=>",

    # Common fractions
    "\u00BD": "1/2",
    "\u00BC": "1/4",
    "\u00BE": "3/4",

    # Trademark symbols
    "\u00A9": "(C)",
    "\u00AE": "(R)",
    "\u2122": "(TM)",

    # Emojis commonly seen in LLM output
    "✅": "[PASS]",
    "✔️": "[PASS]",
    "❌": "[FAIL]",
    "✖️": "[FAIL]",
    "⚠️": "[WARNING]",
    "⚠": "[WARNING]",
    "ℹ️": "[INFO]",
    "ℹ": "[INFO]",
    "⭐": "*",
    "★": "*",
    "→": "->",
    "←": "<-",
}

    def sanitize(text: str) -> str:
        """
        1) Replace known Unicode punctuation with ASCII equivalents (these
           pass cp1252 encoding fine but aren't in the helvetica font).
        2) Fall back to cp1252 encode/decode with errors='replace' to
           catch anything else the font can't render (non-Latin scripts,
           emoji, etc.), swapping it for '?' instead of crashing.
        """
        if text is None:
            return ""
        text = str(text)
        for bad, good in _UNICODE_REPLACEMENTS.items():
            text = text.replace(bad, good)
        return text.encode("cp1252", errors="replace").decode("cp1252")

    def hard_wrap(text: str, max_chunk_chars: int = 30) -> str:
        """Sanitize, then force breakable spaces into any long unbroken token."""
        text = sanitize(text)
        words = text.split(" ")
        wrapped_words = []
        for word in words:
            if len(word) <= max_chunk_chars:
                wrapped_words.append(word)
            else:
                chunks = [word[i:i + max_chunk_chars] for i in range(0, len(word), max_chunk_chars)]
                wrapped_words.append(" ".join(chunks))
        return " ".join(wrapped_words)

    def full_width_multi_cell(h: float, text: str) -> None:
        """
        Always reset x to the left margin and pass an EXPLICIT width
        (pdf.epw) rather than 0, so a prior cell/ln call can't leave the
        cursor somewhere that shrinks the computed width to near-zero.
        """
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, h, text)

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_x(pdf.l_margin)
    pdf.cell(pdf.epw, 10, "VeriFact AI - Verification Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(4)

    def write_field(label: str, value: str) -> None:
        pdf.set_font("Helvetica", "B", 11)
        full_width_multi_cell(7, hard_wrap(label))
        pdf.set_font("Helvetica", "", 11)
        full_width_multi_cell(7, hard_wrap(value))
        pdf.ln(2)

    write_field("Claim:", result.claim)
    write_field("Decision:", result.verdict.value)
    write_field("Confidence:", result.confidence_percent())
    write_field("Reason:", result.reason)

    if result.evidence_chunks:
        pdf.set_font("Helvetica", "B", 11)
        full_width_multi_cell(7, "Evidence:")
        pdf.set_font("Helvetica", "", 10)
        for chunk in result.evidence_chunks:
            full_width_multi_cell(6, hard_wrap(f'- "{chunk.text}" ({chunk.source_title})'))
        pdf.ln(2)

    if result.sources:
        pdf.set_font("Helvetica", "B", 11)
        full_width_multi_cell(7, "Sources:")
        pdf.set_font("Helvetica", "", 10)
        for src in result.sources:
            full_width_multi_cell(6, hard_wrap(src))

    output = pdf.output()
    if isinstance(output, str):
        return output.encode("latin-1")
    return bytes(output)