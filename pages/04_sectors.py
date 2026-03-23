"""
pages/04_sectors.py
====================
Sector deep-dive: heatmap multi-timeframe, rotation, lifecycle, reflexivity.
"""

import streamlit as st
import plotly.graph_objects as go
from intelligence.master_engine import run_intelligence
from ui.components.shared import (
    section_header, chart_sector_heatmap, sector_row,
    score_color, sm_tag, fmt
)
from config.settings import LIFECYCLE_STAGES, PHASE_COLORS


def main():
    st.markdown('<div style="color:#4a9eff;font-family:Syne,sans-serif;font-size:22px;font-weight:800;margin-bottom:16px;">↻ Sector Intelligence</div>', unsafe_allow_html=True)

    with st.spinner("Loading sector data..."):
        intel = run_intelligence()

    tabs = st.tabs(["HEATMAP", "ROTATION", "LIFECYCLE", "REFLEXIVITY", "52W CONTEXT"])

    # ── HEATMAP TAB
    with tabs[0]:
        section_header("▦ SECTOR HEATMAP — Multi-timeframe")
        tf_key = "sec_heatmap_tf"
        if tf_key not in st.session_state:
            st.session_state[tf_key] = "1D"
        c1,c2,c3,c4,_ = st.columns([1,1,1,1,5])
        for col_obj, tf in zip([c1,c2,c3,c4], ["1D","5D","1M","3M"]):
            with col_obj:
                if st.button(tf, key=f"sec_tf_{tf}",
                             type="primary" if st.session_state[tf_key]==tf else "secondary"):
                    st.session_state[tf_key] = tf
                    st.rerun()
        fig = chart_sector_heatmap(intel.sector_data, st.session_state[tf_key])
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False}, key="sec_heatmap")

        # Table below heatmap
        tf_field = {"1D":"chg","5D":"return5d","1M":"return20d","3M":"return60d"}.get(st.session_state[tf_key],"chg")
        valid = [s for s in intel.sector_data if s.valid]
        sorted_s = sorted(valid, key=lambda x: getattr(x, tf_field, 0), reverse=True)
        for s in sorted_s:
            val = getattr(s, tf_field, 0)
            val_col = "#00ff88" if val > 0 else "#ff4444"
            pos = s.pos52
            pos_str = f"{pos:.0f}% of 52W range" if pos is not None else ""
            st.markdown(f"""
            <div style="background:#060f1e;border:1px solid #0f2440;border-radius:5px;
                        padding:7px 14px;margin-bottom:3px;display:flex;
                        align-items:center;justify-content:space-between">
                <span style="color:#e2eef8;font-family:JetBrains Mono,monospace;
                             font-size:12px;font-weight:600;min-width:60px">{s.short}</span>
                <span style="color:#4a6a8a;font-family:JetBrains Mono,monospace;
                             font-size:10px;flex:1">{s.name}</span>
                <span style="color:{val_col};font-family:JetBrains Mono,monospace;
                             font-size:11px;min-width:65px;text-align:right">{val:+.2f}%</span>
                <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;
                             font-size:9px;min-width:120px;text-align:right">{pos_str}</span>
                <span style="margin-left:10px">{sm_tag(s.sm.signal)}</span>
            </div>""", unsafe_allow_html=True)

    # ── ROTATION TAB
    with tabs[1]:
        section_header("↻ ROTATION MAP — RS vs Nifty (20D×60% + 5D×40%)")

        # Chart: bar for r20, line for r5
        names  = [s.short for s in intel.ranked]
        r20    = [s.return20d for s in intel.ranked]
        r5     = [s.return5d  for s in intel.ranked]
        rs_arr = [s.rs_vs_nifty for s in intel.ranked]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="RS vs Nifty (20D)", x=names, y=rs_arr,
            marker_color=["#00ff88" if v > 0 else "#ff4444" for v in rs_arr],
            hovertemplate="%{x}: RS %{y:+.1f}%<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            name="5D Return", x=names, y=r5, mode="markers+lines",
            marker=dict(color="#ffb300", size=7),
            line=dict(color="#ffb300", width=1.5, dash="dot"),
        ))
        fig.add_hline(y=0, line_color="#1e3a5f", line_width=1)
        fig.update_layout(
            paper_bgcolor="#030712", plot_bgcolor="#060f1e",
            font=dict(family="JetBrains Mono", color="#b8d4ec", size=9),
            height=300, barmode="group", showlegend=True,
            legend=dict(orientation="h", x=0, y=1.12, font=dict(size=9)),
            xaxis=dict(showgrid=False, color="#3a5a7f"),
            yaxis=dict(showgrid=True, gridcolor="#0f2440", color="#3a5a7f"),
            margin=dict(l=8, r=8, t=40, b=8),
            title=dict(text="Sector RS vs Nifty + 5D Return",
                       font=dict(size=10, color="#4a9eff"), x=0),
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False}, key="rot_chart")

        for i, s in enumerate(intel.ranked, 1):
            sector_row(s, i, show_lifecycle=True)

    # ── LIFECYCLE TAB
    with tabs[2]:
        section_header("◉ SECTOR LIFECYCLE — Neglected → Discovered → Consensus → Crowded → Abandoned")
        st.markdown("""
        <div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:9px;
                    margin-bottom:12px;line-height:1.7">
        The best entries are in the Neglected→Discovered transition — before consensus forms.
        Crowded sectors have high momentum but diminishing return per unit of risk.
        Abandoned sectors are contrarian opportunities when fundamentals haven't deteriorated.
        </div>""", unsafe_allow_html=True)

        for lc in intel.lifecycles:
            lc_cfg = LIFECYCLE_STAGES.get(lc.stage, LIFECYCLE_STAGES.get("transition",{}))
            col    = lc_cfg.get("color", "#4a9eff")
            bonus  = lc_cfg.get("score_bonus", 0)
            bonus_str = f"(+{bonus} pts)" if bonus > 0 else f"({bonus} pts)" if bonus < 0 else ""
            ev_html = " · ".join(lc.evidence) if lc.evidence else ""

            st.markdown(f"""
            <div style="background:#060f1e;border:1px solid #0f2440;
                        border-left:3px solid {col};border-radius:6px;
                        padding:10px 16px;margin-bottom:5px">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                    <span style="color:#e2eef8;font-family:JetBrains Mono,monospace;
                                 font-size:12px;font-weight:600">{lc.sector}</span>
                    <span style="color:{col};font-family:JetBrains Mono,monospace;
                                 font-size:10px;font-weight:700">{lc.stage.upper()} {bonus_str}</span>
                </div>
                <div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:9px">
                    {ev_html}
                </div>
            </div>""", unsafe_allow_html=True)

    # ── REFLEXIVITY TAB
    with tabs[3]:
        section_header("◈ REFLEXIVITY METER — Price vs Fundamental Momentum Gap")
        st.markdown("""
        <div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:9px;
                    margin-bottom:12px;line-height:1.7">
        Based on Soros reflexivity theory: when price momentum significantly exceeds fundamental
        improvement rate, the feedback loop is maturing. Bust risk rises. Entry risk rises.
        When fundamentals improve but price lags — potential Neglected→Discovered transition.
        </div>""", unsafe_allow_html=True)

        stage_colors = {
            "LOOP_TOP":       "#ff4444",
            "MATURING_LOOP":  "#ffb300",
            "EARLY_LOOP":     "#4a9eff",
            "FUNDAMENTAL_LED":"#00ff88",
            "NEGLECTED":      "#00dd88",
            "UNKNOWN":        "#3a5a7f",
        }
        for r in intel.reflexivity:
            col = stage_colors.get(r.stage, "#4a9eff")
            st.markdown(f"""
            <div style="background:#060f1e;border:1px solid #0f2440;border-radius:6px;
                        padding:10px 14px;margin-bottom:5px">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                    <span style="color:#e2eef8;font-family:JetBrains Mono,monospace;
                                 font-size:12px;font-weight:600">{r.sector}</span>
                    <span style="color:{col};font-family:JetBrains Mono,monospace;
                                 font-size:11px;font-weight:700">{r.stage}</span>
                </div>
                <div style="display:flex;gap:16px">
                    <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px">
                        Price 60D: <span style="color:{'#00ff88' if r.price_momentum>0 else '#ff4444'}">{r.price_momentum:+.1f}%</span>
                    </span>
                    <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px">
                        Fund. Score: <span style="color:#4a9eff">{r.fundamental_score:.0f}/100</span>
                    </span>
                    <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px">
                        Gap: <span style="color:{col}">{r.gap:+.0f}</span>
                    </span>
                    <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px">
                        Conviction: <span style="color:#b8d4ec">{r.conviction}</span>
                    </span>
                </div>
            </div>""", unsafe_allow_html=True)

    # ── 52W CONTEXT TAB
    with tabs[4]:
        section_header("📍 52-WEEK RANGE CONTEXT")
        from data.market_data import fetch_market_data
        from config.settings import INDEX_SYMBOLS
        from core.math_utils import pct_of_range
        quotes = fetch_market_data()

        items = [("Nifty 50","^NSEI"),("Bank Nifty","^NSEBANK"),("India VIX","^INDIAVIX")] + \
                [(s.name, s.sym) for s in intel.sector_data if s.valid]

        for name, sym in items:
            q = quotes.get(sym)
            if not q or not q.loaded:
                continue
            pos = pct_of_range(q.price, q.l52, q.h52)
            if pos is None:
                continue
            bar_col = "#00ff88" if pos >= 50 else "#4a9eff" if pos >= 20 else "#ff8844"
            lbl = "NEAR HIGH" if pos >= 80 else "UPPER HALF" if pos >= 50 else "LOWER HALF" if pos >= 20 else "NEAR LOW"
            lbl_col = "#ffb300" if pos >= 80 else "#00ff88" if pos >= 50 else "#4a9eff" if pos >= 20 else "#00ff88"
            h52 = q.h52 or 0; l52 = q.l52 or 0
            st.markdown(f"""
            <div style="background:#060f1e;border:1px solid #0f2440;border-radius:6px;
                        padding:9px 14px;margin-bottom:4px">
                <div style="display:flex;justify-content:space-between;margin-bottom:5px">
                    <span style="color:#e2eef8;font-family:JetBrains Mono,monospace;
                                 font-size:11px;font-weight:500;min-width:130px">{name}</span>
                    <span style="color:#b8d4ec;font-family:JetBrains Mono,monospace;
                                 font-size:11px;min-width:80px;text-align:right">
                        {q.price:,.1f}</span>
                    <span style="color:{lbl_col};font-family:JetBrains Mono,monospace;
                                 font-size:9px;min-width:80px;text-align:right">{lbl}</span>
                    <span style="color:#4a6a8a;font-family:JetBrains Mono,monospace;
                                 font-size:9px;min-width:55px;text-align:right">
                        {pos:.0f}% range</span>
                </div>
                <div style="display:flex;align-items:center;gap:6px">
                    <span style="color:#2a4a6f;font-family:JetBrains Mono,monospace;
                                 font-size:8px;min-width:55px">{l52:,.0f}</span>
                    <div style="flex:1;background:#0a1628;border-radius:2px;height:5px">
                        <div style="width:{pos:.0f}%;height:100%;background:{bar_col};
                                    border-radius:2px;transition:width .8s;max-width:100%"></div>
                    </div>
                    <span style="color:#2a4a6f;font-family:JetBrains Mono,monospace;
                                 font-size:8px;min-width:55px;text-align:right">{h52:,.0f}</span>
                </div>
            </div>""", unsafe_allow_html=True)


main()
