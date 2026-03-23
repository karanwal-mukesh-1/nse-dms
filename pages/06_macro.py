"""pages/06_macro.py"""
import streamlit as st
import plotly.graph_objects as go
from intelligence.master_engine import run_intelligence
from intelligence.sector_engine import compute_commodity_spillover, get_rate_cycle_stage
from data.market_data import fetch_commodities, fetch_india_10y_yield
from data.nse_data import fetch_fii_dii_flow
from ui.components.shared import section_header

def main():
    st.markdown('<div style="color:#4a9eff;font-family:Syne,sans-serif;font-size:22px;font-weight:800;margin-bottom:16px;">🌐 Macro & Global Intelligence</div>', unsafe_allow_html=True)
    with st.spinner("Loading macro data..."):
        intel       = run_intelligence()
        commodities = fetch_commodities()
        fii_data    = fetch_fii_dii_flow()
        yield_val   = fetch_india_10y_yield()

    tabs = st.tabs(["COMMODITIES", "RATE CYCLE", "FII/DII FLOW", "PCR SENTIMENT"])

    with tabs[0]:
        section_header("🌐 GLOBAL COMMODITY SPILLOVER — NSE Impact")
        spillovers = compute_commodity_spillover(commodities, intel.sector_data)
        if spillovers:
            for sp in spillovers:
                urg_col = "#ff4444" if sp["urgency"] == "HIGH" else "#ffb300"
                st.markdown(f"""
                <div style="background:#060f1e;border:1px solid #0f2440;border-left:3px solid {urg_col};border-radius:6px;padding:10px 16px;margin-bottom:5px">
                    <div style="color:#e2eef8;font-family:JetBrains Mono,monospace;font-size:10px;line-height:1.6">{sp["message"]}</div>
                    <div style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:8px;margin-top:3px">Urgency: {sp["urgency"]}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No significant commodity moves (threshold: >2% in 5 days).")

        st.markdown("<br>", unsafe_allow_html=True)
        section_header("COMMODITY PRICES")
        if commodities:
            cols = st.columns(3)
            for i, c in enumerate(commodities):
                with cols[i % 3]:
                    chg_col = "#00ff88" if c.chg_5d_pct >= 0 else "#ff4444"
                    st.markdown(f"""
                    <div style="background:#060f1e;border:1px solid #0f2440;border-radius:6px;padding:10px 14px;margin-bottom:8px">
                        <div style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:8px;margin-bottom:3px">{c.symbol}</div>
                        <div style="color:#e2eef8;font-family:JetBrains Mono,monospace;font-size:14px;font-weight:700">{c.name}</div>
                        <div style="color:#b8d4ec;font-family:JetBrains Mono,monospace;font-size:12px">{c.price:.2f}</div>
                        <div style="color:{chg_col};font-family:JetBrains Mono,monospace;font-size:10px">5D: {c.chg_5d_pct:+.2f}%</div>
                        {f'<div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:8px;margin-top:3px">→ {", ".join(c.nse_sectors)}</div>' if c.nse_sectors else ""}
                    </div>""", unsafe_allow_html=True)

    with tabs[1]:
        section_header("◉ RATE CYCLE POSITIONING")
        playbook = get_rate_cycle_stage(intel.vix_slope, intel.nifty_r20, yield_val)
        stage_col = {"cutting_aggressive":"#00ff88","cutting_moderate":"#44dd88","neutral":"#ffb300","hiking":"#ff4444"}.get(playbook.get("current_stage","neutral"),"#4a9eff")
        st.markdown(f"""
        <div style="background:#060f1e;border:1px solid #0f2440;border-left:3px solid {stage_col};border-radius:8px;padding:16px 20px;margin-bottom:16px">
            <div style="color:{stage_col};font-family:JetBrains Mono,monospace;font-size:12px;font-weight:700;margin-bottom:6px">{playbook.get("current_stage","UNKNOWN").upper().replace("_"," ")}</div>
            <div style="color:#b8d4ec;font-family:JetBrains Mono,monospace;font-size:10px;margin-bottom:8px">{playbook.get("description","")}</div>
            <div style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px">Estimated India 10Y yield: {yield_val:.2f}% (proxy)</div>
        </div>""", unsafe_allow_html=True)

        col_out, col_under = st.columns(2)
        with col_out:
            section_header("▶ OUTPERFORM IN THIS CYCLE")
            for s in playbook.get("outperform", []):
                st.markdown(f'<div style="color:#00ff88;font-family:JetBrains Mono,monospace;font-size:11px;margin-bottom:3px">✓ {s}</div>', unsafe_allow_html=True)
        with col_under:
            section_header("✕ UNDERPERFORM IN THIS CYCLE")
            for s in playbook.get("underperform", []):
                st.markdown(f'<div style="color:#ff4444;font-family:JetBrains Mono,monospace;font-size:11px;margin-bottom:3px">✗ {s}</div>', unsafe_allow_html=True)

        st.markdown(f'<div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:10px;margin-top:10px">{playbook.get("positioning","")}</div>', unsafe_allow_html=True)

    with tabs[2]:
        section_header("🏦 FII / DII PROVISIONAL FLOW")
        if not fii_data:
            st.info("NSE FII/DII endpoint unavailable from cloud servers. Check nseindia.com → Market Data → FII/DII Activity.")
        else:
            recent_fii = sum(r["fii_net"] for r in fii_data[:5])
            recent_dii = sum(r["dii_net"] for r in fii_data[:5])
            m1,m2,m3 = st.columns(3)
            with m1: st.metric("FII 5D Net", f"₹{recent_fii:,.0f} Cr", delta="BUYING" if recent_fii>0 else "SELLING")
            with m2: st.metric("DII 5D Net", f"₹{recent_dii:,.0f} Cr", delta="BUYING" if recent_dii>0 else "SELLING")
            with m3: st.metric("Combined Net", f"₹{recent_fii+recent_dii:,.0f} Cr")

            dates=[r["date"] for r in reversed(fii_data)]
            fii_v=[r["fii_net"] for r in reversed(fii_data)]
            dii_v=[r["dii_net"] for r in reversed(fii_data)]
            fig=go.Figure()
            fig.add_trace(go.Bar(name="FII Net",x=dates,y=fii_v,marker_color=["#00ff88" if v>0 else "#ff4444" for v in fii_v]))
            fig.add_trace(go.Bar(name="DII Net",x=dates,y=dii_v,marker_color=["#4a9eff" if v>0 else "#ffb300" for v in dii_v]))
            fig.add_hline(y=0,line_color="#1e3a5f",line_width=1)
            fig.update_layout(paper_bgcolor="#030712",plot_bgcolor="#060f1e",font=dict(family="JetBrains Mono",color="#b8d4ec",size=9),height=280,barmode="group",showlegend=True,legend=dict(orientation="h",x=0,y=1.12,font=dict(size=9)),xaxis=dict(showgrid=False,color="#3a5a7f"),yaxis=dict(showgrid=True,gridcolor="#0f2440"),margin=dict(l=8,r=8,t=40,b=8),title=dict(text="FII / DII Daily Net Flow (₹ Crore)",font=dict(size=10,color="#4a9eff"),x=0))
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False},key="fii_chart")

    with tabs[3]:
        section_header("◉ PUT/CALL RATIO SENTIMENT")
        from data.market_data import fetch_put_call_ratio
        pcr = fetch_put_call_ratio()
        if pcr:
            sig_col={"COMPLACENT":"#ff4444","FEARFUL":"#00ff88","NEUTRAL":"#ffb300"}.get(pcr["signal"],"#4a9eff")
            st.markdown(f"""
            <div style="background:#060f1e;border:1px solid #0f2440;border-radius:8px;padding:16px 20px;margin-bottom:16px">
                <div style="color:{sig_col};font-family:JetBrains Mono,monospace;font-size:14px;font-weight:700;margin-bottom:6px">{pcr["signal"]}</div>
                <div style="color:#b8d4ec;font-family:JetBrains Mono,monospace;font-size:11px;margin-bottom:4px">Estimated PCR: {pcr["pcr_estimated"]:.2f}</div>
                <div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:9px">{pcr["note"]}</div>
            </div>""", unsafe_allow_html=True)
            st.markdown("""
            <div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:9px;line-height:1.7">
            COMPLACENT (low PCR): Retail buying calls aggressively — bearish contrarian signal<br>
            FEARFUL (high PCR): Protective puts being bought — potential bullish reversal near<br>
            NEUTRAL: No strong sentiment extreme
            </div>""", unsafe_allow_html=True)

main()
