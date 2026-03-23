"""pages/08_history.py"""
import streamlit as st
import plotly.graph_objects as go
from intelligence.master_engine import run_intelligence
from ui.components.shared import section_header


def main():
    st.markdown('<div style="color:#4a9eff;font-family:Syne,sans-serif;font-size:22px;font-weight:800;margin-bottom:16px;">📈 Score History</div>', unsafe_allow_html=True)

    with st.spinner("Loading..."):
        intel = run_intelligence()

    history = st.session_state.get("score_history", [])

    if len(history) < 2:
        st.info("Score history builds as you use the app. Each refresh adds an entry. Come back after a few sessions.")
    else:
        # Sparkline
        times  = [h["time"]     for h in history]
        scores = [h["score"]    for h in history]
        decs   = [h["decision"] for h in history]
        colors = {"STRONG YES":"#00ff88","YES":"#00dd77","CAUTION":"#ffb300","NO":"#ff4444"}
        mcolors = [colors.get(d,"#4a9eff") for d in decs]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=times, y=scores, mode="lines+markers",
            line=dict(color="#4a9eff", width=2),
            marker=dict(color=mcolors, size=8, line=dict(color="#030712", width=1)),
            fill="tozeroy", fillcolor="rgba(74,158,255,0.06)",
            hovertemplate="<b>%{x}</b><br>Score: %{y}/100<extra></extra>",
        ))
        fig.add_hline(y=82, line_color="#00ff88", line_width=1, line_dash="dot")
        fig.add_hline(y=72, line_color="#44dd88", line_width=1, line_dash="dot")
        fig.add_hline(y=58, line_color="#ffb300", line_width=1, line_dash="dot")
        fig.update_layout(
            paper_bgcolor="#030712", plot_bgcolor="#060f1e",
            font=dict(family="JetBrains Mono", color="#b8d4ec", size=9),
            height=220, showlegend=False,
            xaxis=dict(showgrid=False, color="#3a5a7f", tickfont=dict(size=8)),
            yaxis=dict(showgrid=True, gridcolor="#0f2440", color="#3a5a7f", range=[0,100]),
            margin=dict(l=8, r=8, t=32, b=8),
            title=dict(text="Market Quality Score — Session Log", font=dict(size=10, color="#4a9eff"), x=0),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="hist_chart")

        # Trend summary
        if len(scores) >= 3:
            trend = scores[-1] - scores[-3]
            trend_col = "#00ff88" if trend > 3 else "#ff4444" if trend < -3 else "#ffb300"
            trend_lbl = "IMPROVING" if trend > 3 else "DETERIORATING" if trend < -3 else "STABLE"
            st.markdown(f'<div style="color:{trend_col};font-family:JetBrains Mono,monospace;font-size:11px;margin-bottom:12px">Environment trend: {trend_lbl} ({trend:+.0f} pts over last 3 readings)</div>', unsafe_allow_html=True)

        section_header("SESSION LOG")
        for h in reversed(history):
            d_col = {"STRONG YES":"#00ff88","YES":"#00dd77","CAUTION":"#ffb300","NO":"#ff4444"}.get(h["decision"],"#4a9eff")
            p_col = {"STRONG TREND":"#00ff88","EARLY TREND":"#44dd88","LATE TREND":"#ffb300","DISTRIBUTION":"#ff4444","CONSOLIDATION":"#4a9eff"}.get(h["phase"],"#4a9eff")
            st.markdown(f"""
            <div style="background:#060f1e;border:1px solid #0f2440;border-radius:5px;
                        padding:7px 14px;margin-bottom:3px;display:flex;
                        align-items:center;justify-content:space-between">
                <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:10px;min-width:100px">{h["time"]}</span>
                <span style="color:{d_col};font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;min-width:80px">{h["decision"]}</span>
                <span style="color:#b8d4ec;font-family:JetBrains Mono,monospace;font-size:12px;min-width:60px">{h["score"]}/100</span>
                <span style="color:{p_col};font-family:JetBrains Mono,monospace;font-size:10px">{h["phase"]}</span>
            </div>""", unsafe_allow_html=True)

        if st.button("Clear History", key="clear_hist"):
            st.session_state["score_history"] = []
            st.rerun()

    st.caption("Note: Session history resets on Streamlit server restart. For persistent history, a database integration would be needed (future version).")


main()
