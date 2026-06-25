import html
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.agent import resolve_anthropic_api_key
from utils.report_generator import generate_toolbox_talk_pdf
from utils.toolbox_talk import (
    INCIDENT_TYPES,
    SEVERITY_LEVELS,
    TRADES,
    generate_toolbox_talk,
)


def render():
    st.markdown("""
<div style="margin-bottom:20px; padding-bottom:16px; border-bottom:1px solid #1A2540;">
    <div style="font-size:11px; color:#3D5068; letter-spacing:1.5px;
                text-transform:uppercase; margin-bottom:6px; font-weight:600;">
        SAPIENTIA AI · MODULE 2
    </div>
    <h1 style="font-size:26px; font-weight:700; color:#F1F5F9;
               margin:0; letter-spacing:-0.3px;">
        Toolbox Talk Generator
    </h1>
</div>
""", unsafe_allow_html=True)

    api_key = resolve_anthropic_api_key(st.session_state.get("anthropic_api_key", ""))
    if not api_key:
        st.markdown(
            '<div class="info-box"><strong>Free demo mode — no API key required.</strong> '
            "Generates template toolbox talks from built-in safety content. "
            "Add an optional Anthropic key in Settings for AI-written talks.</div>",
            unsafe_allow_html=True,
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        trade = st.selectbox("Trade", TRADES, key="tt_trade")
    with col2:
        incident_type = st.selectbox("Incident type", INCIDENT_TYPES, key="tt_incident")
    with col3:
        severity = st.selectbox("Severity level", SEVERITY_LEVELS, key="tt_severity")

    st.markdown("<br/>", unsafe_allow_html=True)

    if st.button("Generate Toolbox Talk →", type="primary", use_container_width=True, key="tt_generate"):
        with st.spinner("Generating safety talk…"):
            try:
                talk = generate_toolbox_talk(trade, incident_type, severity, api_key=api_key)
            except Exception as e:
                st.error(f"Toolbox talk generation failed: {e}")
                return
        st.session_state["toolbox_talk_result"] = talk
        st.session_state.pop("_tt_pdf_bytes", None)
        st.session_state.pop("_tt_pdf_fname", None)

    talk = st.session_state.get("toolbox_talk_result")
    if not talk:
        st.markdown(
            '<div class="info-box">Select trade, incident type, and severity, then click '
            "<strong>Generate Toolbox Talk</strong> for a ~10-minute field briefing (400–600 words).</div>",
            unsafe_allow_html=True,
        )
        return

    word_count = talk.get("word_count", 0)
    mode = (talk.get("_llm") or {}).get("mode", "unknown")

    st.markdown(
        f'<div class="sap-glass-panel sap-result-hero">'
        f'<div style="font-size:14px;color:#8899AA;margin-bottom:8px;">Talk ready</div>'
        f'<span class="sap-meta-chip">{html.escape(talk.get("trade", ""))}</span>'
        f'<span class="sap-meta-chip">{html.escape(talk.get("incident_type", ""))}</span>'
        f'<span class="sap-meta-chip">{html.escape(talk.get("severity", ""))}</span>'
        f'<div style="margin-top:10px;font-size:13px;color:#3D5068;">'
        f"{word_count} words · {html.escape(mode)}</div></div>",
        unsafe_allow_html=True,
    )

    full_text = talk.get("full_text", "")

    st.markdown(
        '<p class="sap-label-upper" style="margin:14px 0 8px;">Full talk (copy-ready)</p>',
        unsafe_allow_html=True,
    )
    st.text_area(
        "Toolbox talk text",
        value=full_text,
        height=420,
        label_visibility="collapsed",
        key="tt_display_text",
    )

    behaviors = talk.get("corrective_behaviors") or []
    if behaviors:
        beh_html = "".join(
            f'<div style="display:flex;gap:8px;margin-bottom:6px;">'
            f'<span style="color:#00E5FF;font-weight:700;">{i}.</span>'
            f'<span style="font-size:14px;color:#8899AA;">{html.escape(str(b))}</span></div>'
            for i, b in enumerate(behaviors, 1)
        )
        st.markdown(
            f'<div class="sap-glass-panel"><div class="sap-label-upper">Five corrective behaviors</div>{beh_html}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if st.button("📄 Generate PDF", key="tt_gen_pdf"):
        try:
            pdf_bytes = generate_toolbox_talk_pdf(talk)
            slug = f"{talk.get('trade', 'talk')}_{talk.get('incident_type', 'safety')}".replace(" ", "_").lower()
            st.session_state["_tt_pdf_bytes"] = pdf_bytes
            st.session_state["_tt_pdf_fname"] = f"toolbox_talk_{slug}.pdf"
            st.success("PDF ready — use **Download PDF** below.")
        except ImportError:
            st.error("ReportLab not installed. Run: pip install reportlab")
        except Exception as e:
            st.error(f"Error generating PDF: {e}")

    pdf_bytes = st.session_state.get("_tt_pdf_bytes")
    if pdf_bytes:
        fname = st.session_state.get("_tt_pdf_fname") or "toolbox_talk.pdf"
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            key="tt_download_pdf",
            use_container_width=True,
        )

    if talk.get("_api_error"):
        st.caption(f"ℹ️ Demo mode fallback: {str(talk['_api_error'])[:120]}")


if os.environ.get("SAPIENTIA_SKIP_RENDER") != "1":
    render()
