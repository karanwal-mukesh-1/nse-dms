"""
pages/03_opportunities.py
==========================
Stock opportunity screener.
Top stocks within leading sectors, each with full scorecard + trade setup.
"""

import streamlit as st
from intelligence.master_engine import run_intelligence
from ui.components.shared import (
    section_header, render_opportunity_card, render_bulk_deal_row,
    render_insider_row, score_color
)


def main():
    st.markdown("""
    <div style="color:#4a9eff;font-family:Syne,sans-serif;font-size:22px;
                font-weight:800;margin-bottom:16px;">🎯 Opportunities</div>
    """, unsafe_allow_html=True)

    with st.spinner("Screening opportunities..."):
        intel = run_intelligence()

    if intel.decision == "NO":
        st.markdown("""
        <div style="background:#1a0000;border:1px solid #2a0a0a;border-radius:8px;
                    padding:20px;text-align:center;margin-bottom:16px">
            <div style="color:#ff4444;font-family:Syne,sans-serif;font-size:28px;
                        font-weight:700;margin-bottom:8px">DO NOTHING</div>
            <div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:11px;
                        line-height:1.8">
                Market environment does not support new swing trades.<br>
                Score: {}/100 · Phase: {}
            </div>
        </div>""".format(intel.composite, intel.phase), unsafe_allow_html=True)

        section_header("CONDITIONS TO WATCH FOR")
        conditions = [
            f"VIX below 15 (currently {intel.vix_level:.1f if intel.vix_level else 'N/A'})",
            f"Nifty above 50MA (currently {intel.n50:+.1f if intel.n50 is not None else 'N/A'}% away)",
            f"Breadth above 60% (currently {intel.breadth_score:.0f}%)",
            f"Smart money shifts to ACCUMULATION (currently {intel.sm_signal})",
        ]
        for c in conditions:
            st.markdown(
                f'<div style="color:#7aa8cc;font-family:JetBrains Mono,monospace;'
                f'font-size:10px;margin-bottom:5px">→ {c}</div>',
                unsafe_allow_html=True,
            )
        return

    # ── AI TOP OPPORTUNITY
    ai = intel.ai_output
    if ai and ai.get("top_opportunity"):
        st.markdown(f"""
        <div style="background:#001030;border:1px solid #4a9eff40;border-radius:8px;
                    padding:14px 18px;margin-bottom:16px">
            <div style="color:#4a9eff;font-family:JetBrains Mono,monospace;font-size:8px;
                        letter-spacing:.15em;margin-bottom:6px">⚡ AI TOP OPPORTUNITY</div>
            <div style="color:#e2eef8;font-family:JetBrains Mono,monospace;font-size:12px;
                        line-height:1.6">{ai["top_opportunity"]}</div>
            {f'<div style="color:#ff4444;font-family:JetBrains Mono,monospace;font-size:10px;margin-top:6px">STOP: {ai["stop_condition"]}</div>' if ai.get("stop_condition") else ""}
        </div>""", unsafe_allow_html=True)

    # ── OPPORTUNITIES
    if not intel.opportunities:
        st.info("No opportunities screened yet. Data may still be loading — try refreshing.")
        return

    section_header(f"◎ TOP {len(intel.opportunities)} OPPORTUNITIES — {intel.decision} ENVIRONMENT")

    # Filter controls
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        min_score = st.selectbox("Min Score", [40, 50, 60, 70, 80], index=1, key="opp_min_score")
    with col_f2:
        setup_filter = st.selectbox("Setup Type", ["ALL", "MOMENTUM_CONTINUATION",
                                                    "PULLBACK_TO_20MA", "EARLY_RECOVERY",
                                                    "INSTITUTIONAL_BUY"], key="opp_setup")
    with col_f3:
        show_only_bulk = st.checkbox("Show only with Bulk/Insider signal", key="opp_bulk_only")

    filtered = [o for o in intel.opportunities if o.score >= min_score]
    if setup_filter != "ALL":
        filtered = [o for o in filtered if o.setup_type == setup_filter]
    if show_only_bulk:
        filtered = [o for o in filtered if o.bulk_deal or o.insider]

    if not filtered:
        st.warning("No opportunities match the current filters.")
    else:
        for i, opp in enumerate(filtered, 1):
            render_opportunity_card(opp, rank=i)

    st.markdown("---")

    # ── RECENT BULK DEALS (contextual)
    if intel.bulk_deals:
        section_header(f"💰 RECENT BULK DEALS ({len(intel.bulk_deals)} transactions)")
        buy_deals  = [d for d in intel.bulk_deals if d.deal_type == "BUY"][:8]
        sell_deals = [d for d in intel.bulk_deals if d.deal_type == "SELL"][:4]

        if buy_deals:
            st.markdown('<div style="color:#00ff88;font-family:JetBrains Mono,monospace;font-size:9px;margin-bottom:6px">▶ BUY TRANSACTIONS</div>', unsafe_allow_html=True)
            for d in buy_deals:
                render_bulk_deal_row(d)

        if sell_deals:
            st.markdown('<div style="color:#ff4444;font-family:JetBrains Mono,monospace;font-size:9px;margin:10px 0 6px">✕ SELL TRANSACTIONS</div>', unsafe_allow_html=True)
            for d in sell_deals:
                render_bulk_deal_row(d)
    else:
        st.caption("Bulk deal data unavailable — NSE endpoint may be rate-limiting from cloud server.")

    # ── INSIDER ACTIVITY
    if intel.insider_activity:
        section_header(f"👤 INSIDER ACTIVITY ({len(intel.insider_activity)} disclosures)")
        for act in intel.insider_activity[:10]:
            render_insider_row(act)
    else:
        st.caption("Insider activity data unavailable — NSE PIT endpoint may be rate-limiting.")

    st.markdown("""
    <div style="color:#1e3a5f;font-family:JetBrains Mono,monospace;font-size:8px;
                margin-top:12px;line-height:1.6">
    ⚠ All signals are probabilistic proxies based on publicly available data.
    Volume-based smart money is NOT delivery %, OI, or actual institutional flow data.
    Bulk deal data is end-of-day (T+1). Not investment advice.
    </div>""", unsafe_allow_html=True)


main()
