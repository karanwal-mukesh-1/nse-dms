"""
pages/02_overview.py
=====================
Full market overview: scores, phase, contradictions, heatmap, MA chart.
"""

import streamlit as st
from intelligence.master_engine import run_intelligence
from ui.components.shared import (
    section_header, render_decision_badge, render_score_bars,
    render_contradictions, chart_sector_heatmap, chart_nifty_ma,
    sector_row, score_color, fmt
)


def main():
    st.markdown("""
    <div style="color:#4a9eff;font-family:Syne,sans-serif;font-size:22px;
                font-weight:800;margin-bottom:16px;">📊 Market Overview</div>
    """, unsafe_allow_html=True)

    with st.spinner("Loading market intelligence..."):
        intel = run_intelligence()

    # ── ROW 1: Decision + Score bars + Metrics
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        render_decision_badge(intel)

    with col2:
        section_header("▣ SCORE BREAKDOWN")
        render_score_bars(intel)
        b_src_col = "#00ff88" if intel.breadth_source == "real_nifty50" else "#ffb300"
        b_src_lbl = "REAL (Nifty50)" if intel.breadth_source == "real_nifty50" else "Proxy (10 sectors)"
        st.markdown(
            f'<div style="color:{b_src_col};font-family:JetBrains Mono,monospace;'
            f'font-size:8px;margin-top:4px">BREADTH SOURCE: {b_src_lbl}</div>',
            unsafe_allow_html=True,
        )

    with col3:
        section_header("◈ KEY METRICS")
        m1, m2, m3, m4 = st.columns(4)
        vix_d = f"{intel.vix_slope:+.1f}%" if intel.vix_slope else None
        with m1: st.metric("India VIX",   f"{intel.vix_level:.1f}" if intel.vix_level else "N/A",
                            delta=vix_d, delta_color="inverse")
        with m2: st.metric("vs 200MA",    f"{intel.n200:+.1f}%" if intel.n200 is not None else "N/A")
        with m3: st.metric("RSI(14)",     f"{intel.nrsi:.0f}"   if intel.nrsi    else "N/A")
        with m4: st.metric("SM Signal",   intel.sm_signal)

        m5, m6, m7, m8 = st.columns(4)
        with m5: st.metric("Nifty 20D",   f"{intel.nifty_r20:+.1f}%")
        with m6: st.metric("Breadth",     f"{intel.breadth_score:.0f}%")
        with m7: st.metric("Conviction",  intel.conviction.label)
        with m8: st.metric("Valid Sectors",f"{intel.valid_count}/10")

        section_header("⚠ CONTRADICTIONS")
        render_contradictions(intel)

    st.markdown("---")

    # ── ROW 2: Heatmap + Nifty MA
    col_heat, col_ma = st.columns([1, 1])

    with col_heat:
        section_header("▦ SECTOR HEATMAP")
        tf_key = "ov_heatmap_tf"
        if tf_key not in st.session_state:
            st.session_state[tf_key] = "1D"
        tf_cols = st.columns(4)
        for i, tf in enumerate(["1D", "5D", "1M", "3M"]):
            with tf_cols[i]:
                if st.button(tf, key=f"ov_tf_{tf}",
                             type="primary" if st.session_state[tf_key] == tf else "secondary"):
                    st.session_state[tf_key] = tf
                    st.rerun()
        fig = chart_sector_heatmap(intel.sector_data, st.session_state[tf_key])
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False}, key="ov_heatmap_chart")

    with col_ma:
        from data.market_data import fetch_market_data
        from config.settings import INDEX_SYMBOLS
        quotes = fetch_market_data()
        nifty  = quotes.get(INDEX_SYMBOLS["nifty50"])
        if nifty and nifty.loaded:
            fig = chart_nifty_ma(nifty.closes)
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False}, key="ov_nifty_ma")

    st.markdown("---")

    # ── ROW 3: Sector rotation table
    section_header("↻ SECTOR ROTATION — Ranked by RS vs Nifty")
    for i, s in enumerate(intel.ranked, 1):
        sector_row(s, i, show_lifecycle=True)


main()
