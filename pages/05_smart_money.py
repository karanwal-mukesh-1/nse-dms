"""pages/05_smart_money.py"""
import streamlit as st
from intelligence.master_engine import run_intelligence
from data.nse_data import detect_insider_clusters
from ui.components.shared import (
    section_header, render_bulk_deal_row, render_insider_row, sm_tag, score_color
)

def main():
    st.markdown('<div style="color:#4a9eff;font-family:Syne,sans-serif;font-size:22px;font-weight:800;margin-bottom:16px;">💰 Smart Money Intelligence</div>', unsafe_allow_html=True)
    with st.spinner("Loading smart money data..."):
        intel = run_intelligence()

    tabs = st.tabs(["SECTOR SIGNALS", "BULK DEALS", "INSIDER ACTIVITY", "CLUSTERS"])

    with tabs[0]:
        section_header("💰 SMART MONEY PROXY — Sector Signals")
        sm_col = {"ACCUMULATION":"#00ff88","DISTRIBUTION":"#ff4444"}.get(intel.sm_signal,"#ffb300")
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("Aggregate Signal", intel.sm_signal)
        with c2: st.metric("Avg Score", f"{intel.sm_avg:.0f}/100")
        with c3:
            acc = len([s for s in intel.sector_data if s.valid and s.sm.signal in ("ACCUMULATION","COILING","STEALTH ACCUM")])
            st.metric("Accumulating", f"{acc}/{intel.valid_count} sectors")

        st.markdown("<br>", unsafe_allow_html=True)
        for s in intel.ranked:
            if not s.valid: continue
            sm   = s.sm
            col  = score_color(sm.score)
            bar  = min(100, sm.score)
            f    = sm.factors
            st.markdown(f"""
            <div style="background:#060f1e;border:1px solid #0f2440;border-radius:6px;padding:10px 14px;margin-bottom:5px">
                <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                    <div style="display:flex;align-items:center;gap:10px">
                        <span style="color:#e2eef8;font-family:JetBrains Mono,monospace;font-size:12px;font-weight:600;min-width:52px">{s.short}</span>
                        <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px">{s.name}</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:8px">
                        <span style="color:{col};font-family:JetBrains Mono,monospace;font-size:11px;font-weight:600">{sm.score:.0f}/100</span>
                        {sm_tag(sm.signal)}
                    </div>
                </div>
                <div style="background:#0a1628;border-radius:2px;height:4px;margin-bottom:6px">
                    <div style="width:{bar}%;height:4px;background:{col};border-radius:2px"></div>
                </div>
                <div style="display:flex;gap:12px;flex-wrap:wrap">
                    <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px">Vol Ratio: <span style="color:#b8d4ec">{sm.vol_ratio:.2f}x</span></span>
                    <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px">Range Comp: <span style="color:#b8d4ec">{sm.range_comp:.2f}</span></span>
                    <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px">vs 20MA: <span style="color:{'#00ff88' if sm.vs_20ma_pct>0 else '#ff4444'}">{sm.vs_20ma_pct:+.1f}%</span></span>
                    <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px">Vol Expanding: <span style="color:{'#00ff88' if sm.vol_expanding else '#4a6a8a'}">{'YES' if sm.vol_expanding else 'NO'}</span></span>
                </div>
            </div>""", unsafe_allow_html=True)
        st.caption("⚠ Volume-based proxy only. True smart money requires delivery %, OI data (paid APIs).")

    with tabs[1]:
        section_header(f"💰 BULK & BLOCK DEALS ({len(intel.bulk_deals)} transactions)")
        if not intel.bulk_deals:
            st.info("NSE bulk deal endpoint may be rate-limiting from cloud servers. Check nseindia.com directly.")
        else:
            buys  = [d for d in intel.bulk_deals if d.deal_type == "BUY"]
            sells = [d for d in intel.bulk_deals if d.deal_type == "SELL"]
            col_b, col_s = st.columns(2)
            with col_b:
                st.markdown(f'<div style="color:#00ff88;font-family:JetBrains Mono,monospace;font-size:9px;margin-bottom:6px">▶ BUY ({len(buys)})</div>', unsafe_allow_html=True)
                for d in buys[:12]: render_bulk_deal_row(d)
            with col_s:
                st.markdown(f'<div style="color:#ff4444;font-family:JetBrains Mono,monospace;font-size:9px;margin-bottom:6px">✕ SELL ({len(sells)})</div>', unsafe_allow_html=True)
                for d in sells[:8]: render_bulk_deal_row(d)

    with tabs[2]:
        section_header(f"👤 INSIDER / PROMOTER ACTIVITY ({len(intel.insider_activity)} disclosures)")
        if not intel.insider_activity:
            st.info("NSE PIT insider disclosure endpoint may be rate-limiting. Data is published at nseindia.com.")
        else:
            sig_filter = st.selectbox("Filter by Signal", ["ALL","PROMOTER_BUY_NEAR_LOW","PROMOTER_BUY","PLEDGE_REVOKED","PLEDGE_INVOKED","INSIDER_BUY","PROMOTER_SELL"], key="ins_filter")
            filtered = intel.insider_activity if sig_filter == "ALL" else [a for a in intel.insider_activity if a.signal_type == sig_filter]
            for act in filtered[:15]: render_insider_row(act)

    with tabs[3]:
        section_header("🔥 CLUSTER INSIDER BUYING DETECTOR")
        st.markdown('<div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:9px;margin-bottom:10px;line-height:1.7">Cluster buying = 2+ insiders buying within a short window. Highest-conviction insider signal. When near 52W low = exceptional setup.</div>', unsafe_allow_html=True)
        clusters = detect_insider_clusters(intel.insider_activity)
        if not clusters:
            st.info("No cluster buying detected in available data.")
        else:
            for cl in clusters:
                col = "#00ff88" if cl["signal"] == "CLUSTER_BUY" else "#4a9eff"
                st.markdown(f"""
                <div style="background:#060f1e;border:1px solid #0f2440;border-left:3px solid {col};border-radius:6px;padding:10px 16px;margin-bottom:6px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                        <span style="color:#e2eef8;font-family:JetBrains Mono,monospace;font-size:13px;font-weight:700">{cl["symbol"]}</span>
                        <span style="color:{col};font-family:JetBrains Mono,monospace;font-size:10px;font-weight:600">{cl["signal"]} {'★'*cl['conviction']}</span>
                    </div>
                    <div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:9px">{cl["count"]} buyers: {', '.join(cl['buyers'][:3])}</div>
                    {f'<div style="color:#b8d4ec;font-family:JetBrains Mono,monospace;font-size:9px;margin-top:3px">Total value: ₹{cl["total_value_cr"]:.2f} Cr</div>' if cl["total_value_cr"] > 0 else ""}
                </div>""", unsafe_allow_html=True)

main()
