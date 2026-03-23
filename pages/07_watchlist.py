"""pages/07_watchlist.py"""
import streamlit as st
from intelligence.master_engine import run_intelligence
from intelligence.opportunity_engine import score_stock
from data.market_data import fetch_stock_data
from ui.components.shared import section_header, render_opportunity_card

def main():
    st.markdown('<div style="color:#4a9eff;font-family:Syne,sans-serif;font-size:22px;font-weight:800;margin-bottom:16px;">◎ Custom Watchlist</div>', unsafe_allow_html=True)

    with st.spinner("Loading intelligence..."):
        intel = run_intelligence()

    section_header("ADD STOCKS TO SCORE")
    st.markdown('<div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:9px;margin-bottom:8px">Enter NSE symbols with .NS suffix (e.g. SBIN.NS, RELIANCE.NS). Comma-separated.</div>', unsafe_allow_html=True)

    syms_input = st.text_input("NSE Symbols (.NS)", placeholder="SBIN.NS, RELIANCE.NS, HDFCBANK.NS", key="watchlist_input", label_visibility="collapsed")
    sector_sel = st.selectbox("Assign to sector (for RS calculation)", options=[s.name for s in intel.sector_data if s.valid], key="wl_sector")

    if st.button("SCORE MY WATCHLIST", key="score_watchlist") and syms_input:
        symbols = tuple(s.strip() for s in syms_input.split(",") if s.strip())
        selected_sector = next((s for s in intel.sector_data if s.name == sector_sel), intel.ranked[0] if intel.ranked else None)

        with st.spinner(f"Fetching data for {len(symbols)} stocks..."):
            stock_data = fetch_stock_data(symbols)

        section_header(f"SCORECARD — {len(symbols)} stocks")
        results = []
        for sym in symbols:
            q = stock_data.get(sym)
            if not q or not q.loaded:
                st.warning(f"{sym}: No data available")
                continue
            if selected_sector:
                opp = score_stock(sym, q, selected_sector, intel.bulk_deals, intel.insider_activity)
                results.append(opp)

        results.sort(key=lambda x: x.score, reverse=True)
        for i, opp in enumerate(results, 1):
            render_opportunity_card(opp, rank=i)

        if not results:
            st.info("No stocks could be scored. Check symbols include .NS suffix.")

    # ── Quick watchlist from top opportunities
    if intel.opportunities:
        st.markdown("---")
        section_header("◎ AUTO-SCREENED OPPORTUNITIES")
        st.markdown('<div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:9px;margin-bottom:8px">Top-scoring stocks from leading sectors, automatically screened.</div>', unsafe_allow_html=True)
        for i, opp in enumerate(intel.opportunities[:5], 1):
            render_opportunity_card(opp, rank=i)

main()
