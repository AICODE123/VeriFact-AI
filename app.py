"""
app.py
======
VeriFact AI — Streamlit main application.

Run with:
    streamlit run app.py

Layout:
- Sidebar: History, Settings, Offline Mode toggle
- Main page: title, claim input, Verify button, output card
"""

from __future__ import annotations

import streamlit as st

from core.pipeline import PipelineError, VerificationPipeline
from ui.components import (
    build_plaintext_summary,
    export_result_to_pdf,
    render_history_list,
    render_verdict_card,
)
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="VeriFact AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def get_pipeline() -> VerificationPipeline:
    """
    Build the VerificationPipeline once per Streamlit server process.

    Loading spaCy / sentence-transformers / the NLI model is expensive, so
    this is cached across reruns and across users of the same server.
    """
    return VerificationPipeline()


def _init_session_state() -> None:
    if "offline_mode" not in st.session_state:
        st.session_state.offline_mode = False
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "claim_input" not in st.session_state:
        st.session_state.claim_input = ""


def render_sidebar() -> None:
    """Render the sidebar: navigation, settings, offline mode."""
    with st.sidebar:
        st.markdown("## 🔍 VeriFact AI")
        st.caption("Explainable, evidence-based fact verification")

        page = st.radio("Navigate", ["Verify a Claim", "History", "Settings"], label_visibility="collapsed")

        st.divider()
        st.markdown("### Offline Mode")
        st.session_state.offline_mode = st.toggle(
            "Use local knowledge base only",
            value=st.session_state.offline_mode,
            help="Skip live web search and answer only from the local offline knowledge base. "
            "Useful when the internet is unavailable.",
        )

        st.divider()
        st.caption("Created by Ridhima Choudhary :)")

    return page


def render_verify_page(pipeline: VerificationPipeline) -> None:
    """Render the main claim-verification page."""
    st.title("VeriFact AI")
    st.write("Enter a factual claim below. VeriFact AI will search trusted sources, weigh the evidence, and explain its verdict.")

    with st.form(key="claim_form"):
        claim = st.text_input(
            "Enter a claim to verify",
            placeholder='e.g. "The Eiffel Tower is located in Berlin."',
            label_visibility="collapsed",
        )
        col1, col2 = st.columns([1, 5])
        with col1:
            submitted = st.form_submit_button("Verify", type="primary", use_container_width=True)

    if submitted:
        if not claim or not claim.strip():
            st.warning("Please enter a claim to verify.")
        else:
            _run_verification(pipeline, claim.strip())

    if st.session_state.last_result is not None:
        st.divider()
        render_verdict_card(st.session_state.last_result)

        pdf_bytes = export_result_to_pdf(st.session_state.last_result)
        st.download_button(
            "⬇️ Export report as PDF",
            data=pdf_bytes,
            file_name="verifact_report.pdf",
            mime="application/pdf",
        )


def _run_verification(pipeline: VerificationPipeline, claim: str) -> None:
    """Execute the pipeline with a progress indicator and store the result."""
    progress_text = "Searching trusted sources and analyzing evidence..."
    progress_bar = st.progress(0, text=progress_text)
    try:
        progress_bar.progress(20, text="Processing claim...")
        progress_bar.progress(45, text="Searching trusted sources...")
        progress_bar.progress(70, text="Retrieving and ranking evidence...")
        progress_bar.progress(90, text="Running verification model...")

        result = pipeline.run(claim, offline_mode=st.session_state.offline_mode)

        progress_bar.progress(100, text="Done.")
        st.session_state.last_result = result
    except PipelineError as exc:
        st.error(f"Could not verify this claim: {exc}")
        logger.error("Pipeline error for claim '%s': %s", claim, exc)
    finally:
        progress_bar.empty()


def render_history_page(pipeline: VerificationPipeline) -> None:
    """Render the verification history page."""
    st.title("History")
    st.write("Your past verification queries, most recent first.")

    entries = pipeline._components.database.get_history()

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🗑️ Clear history"):
            pipeline._components.database.clear_history()
            st.rerun()

    render_history_list(entries)


def render_settings_page() -> None:
    """Render the settings / about page."""
    st.title("Settings")

    st.markdown("### About VeriFact AI")
    st.write(
        "VeriFact AI is an explainable fact-verification assistant. It searches trusted "
        "sources (.gov, .edu, WHO, NASA, UN, Britannica, Wikipedia, and similar), retrieves "
        "relevant evidence, and uses a Natural Language Inference model to determine whether "
        "evidence supports, contradicts, or is insufficient to judge a claim."
    )

    st.markdown("### Pipeline")
    st.code(
        "Claim -> NER -> Search Query -> Trusted Source Search -> Scrape & Chunk "
        "-> Semantic Similarity -> NLI Classification -> Aggregation -> Explanation",
        language=None,
    )

    st.markdown("### Offline Mode")
    st.write(
        "When enabled, VeriFact AI skips live web search entirely and answers only from a "
        "curated local knowledge base of pre-verified facts. This is useful in environments "
        "without internet access, or during live demos where network reliability matters."
    )

    st.markdown("### Disclaimer")
    st.info(
        "VeriFact AI is a student project for educational demonstration purposes. "
        "Verdicts are based on automated NLP analysis of a limited set of trusted sources "
        "and should not be treated as a substitute for professional fact-checking."
    )


def main() -> None:
    _init_session_state()

    with st.spinner("Loading AI models (first run only)..."):
        pipeline = get_pipeline()

    page = render_sidebar()

    if page == "Verify a Claim":
        render_verify_page(pipeline)
    elif page == "History":
        render_history_page(pipeline)
    elif page == "Settings":
        render_settings_page()


if __name__ == "__main__":
    main()
