"""
pages/01_morning_brief.py
==========================
Pre-market checklist — 5 factors, traffic-light status, 60-second read.
AI decision displayed prominently.
This is the page opened every morning before 9:15 AM.
"""

import streamlit as st
from intelligence.master_engine import run_intelligence
from ui.components.shared import (
    section_header, render_decision_badge, render_contradictions, score_color, sm_tag
)
from config.settings import PHASE_COLORS


def check_item(label: str, status: str, detail: str, value: str = ""):
    colors = {"PASS": "#00ff88", "WARN": "#ffb300", "FAIL": "#ff4444"}
    icons  = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}
    col    = colors.get(status, "#4a9eff")
    icon   = icons.get(status, "?")
    st.markdown(f"""
    <div style="background:#060f1e;border:1px solid #0f2440;
                border-left:3px solid {col};border-radius:6px;
                padding:12px 16px;margin-bottom:6px;
                display:flex;align-items:center;justify-content:space-between">
        <div style="display:flex;align-items:center;gap:12px;flex:1">
            <span style="color:{col};font-family:JetBrains Mono,monospace;
                         font-size:16px;min-width:20px">{icon}</span>
            <div>
                <div style="color:#e2eef8;font-family:JetBrains Mono,monospace;
                            font-size:12px;font-weight:600">{label}</div>
                <div style="color:#4a6a8a;font-family:JetBrains Mono,monospace;
                            font-size:9px;margin-top:2px">{detail}</div>
            </div>
        </div>
        <div style="color:{col};font-family:JetBrains Mono,monospace;
                    font-size:12px;font-weight:700;white-space:nowrap;margin-left:12px">
            {value}
        </div>
    </div>""", unsafe_allow_html=True)


def main():
    st.markdown("""
    <div style="margin-bottom:16px">
        <div style="color:#4a9eff;font-family:Syne,sans-serif;font-size:22px;font-weight:800">
            ☀ Morning Brief
        </div>
        <div style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px;
                    letter-spacing:.15em">PRE-MARKET INTELLIGENCE · READ IN 60 SECONDS</div>
    </div>""", unsafe_allow_html=True)

    with st.spinner("Running intelligence pipeline..."):
        intel = run_intelligence()

    col_left, col_right = st.columns([1, 2])

    # ── LEFT: Decision badge + score breakdown
    with col_left:
        render_decision_badge(intel)
        st.markdown("<br>", unsafe_allow_html=True)

        m1, m2 = st.columns(2)
        with m1:
            st.metric("Market Score", f"{intel.composite:.0f}/100")
            st.metric("Phase", intel.phase)
        with m2:
            st.metric("VIX", f"{intel.vix_level:.1f}" if intel.vix_level else "N/A")
            st.metric("Conviction", intel.conviction.label)

    # ── RIGHT: 5-point checklist
    with col_right:
        section_header("5-POINT PRE-MARKET CHECKLIST")

        # Check 1: VIX
        vl = intel.vix_level
        if vl is not None:
            if vl < 15:
                check_item("India VIX", "PASS", f"Fear is low — environment favourable", f"{vl:.1f}")
            elif vl < 20:
                check_item("India VIX", "WARN", f"Moderate volatility — trade selectively", f"{vl:.1f}")
            else:
                check_item("India VIX", "FAIL", f"Elevated fear — reduce or avoid exposure", f"{vl:.1f}")
        else:
            check_item("India VIX", "WARN", "Data unavailable", "---")

        # Check 2: Nifty structure
        n50, n200 = intel.n50, intel.n200
        if n50 is not None and n200 is not None:
            if n50 > 0 and n200 > 0:
                check_item("Nifty Structure", "PASS",
                           f"Above 50MA ({n50:+.1f}%) and 200MA ({n200:+.1f}%) — uptrend intact",
                           intel.phase)
            elif n200 > 0 and n50 < 0:
                check_item("Nifty Structure", "WARN",
                           f"Below 50MA ({n50:+.1f}%) but above 200MA ({n200:+.1f}%) — pullback in uptrend",
                           intel.phase)
            else:
                check_item("Nifty Structure", "FAIL",
                           f"Below 50MA ({n50:+.1f}%) and 200MA ({n200:+.1f}%) — avoid longs",
                           intel.phase)
        else:
            check_item("Nifty Structure", "WARN", "Data unavailable", "---")

        # Check 3: Sector breadth
        n_up    = len([s for s in intel.sector_data if s.valid and s.chg > 0])
        n_total = intel.valid_count or 1
        b_pct   = round(n_up / n_total * 100)
        if b_pct >= 60:
            check_item("Sector Breadth", "PASS",
                       f"{n_up}/{n_total} sectors advancing — broad participation",
                       f"{b_pct}%")
        elif b_pct >= 40:
            check_item("Sector Breadth", "WARN",
                       f"{n_up}/{n_total} sectors advancing — mixed market",
                       f"{b_pct}%")
        else:
            check_item("Sector Breadth", "FAIL",
                       f"Only {n_up}/{n_total} sectors advancing — risk-off tone",
                       f"{b_pct}%")

        # Check 4: Smart money
        sm = intel.sm_signal
        sm_avg = intel.sm_avg
        if sm == "ACCUMULATION":
            check_item("Smart Money Proxy", "PASS",
                       f"Institutional accumulation signals across sectors (avg {sm_avg:.0f}/100)", sm)
        elif sm == "NEUTRAL":
            check_item("Smart Money Proxy", "WARN",
                       f"No clear institutional bias (avg {sm_avg:.0f}/100)", sm)
        else:
            check_item("Smart Money Proxy", "FAIL",
                       f"Distribution pattern — institutions reducing exposure (avg {sm_avg:.0f}/100)", sm)

        # Check 5: Conviction
        conv = intel.conviction
        if conv.score >= 70:
            check_item("Signal Conviction", "PASS",
                       f"{conv.bull}/7 signals bullish — strong agreement", conv.label)
        elif conv.score >= 50:
            check_item("Signal Conviction", "WARN",
                       f"{conv.bull}/7 bullish, {conv.bear}/7 bearish — mixed signals", conv.label)
        else:
            check_item("Signal Conviction", "FAIL",
                       f"Signals conflicting ({conv.bull} bull vs {conv.bear} bear) — avoid trading", conv.label)

    # ── TODAY'S VERDICT
    st.markdown("<br>", unsafe_allow_html=True)
    dc     = {"STRONG YES":"#00ff88","YES":"#00dd77","CAUTION":"#ffb300","NO":"#ff4444"}
    dc_bg  = {"STRONG YES":"#001a0d","YES":"#001508","CAUTION":"#1a1200","NO":"#1a0000"}
    dc_msg = {
        "STRONG YES": "All signals aligned. Full position sizing appropriate. Press when setups confirm.",
        "YES":        "Environment supports active swing trading. Use appropriate size and discipline.",
        "CAUTION":    "Trade only high-conviction A+ setups. Reduce size by half. Be selective.",
        "NO":         "Do not initiate new swing trades. Protect existing positions. Observe.",
    }
    d   = intel.decision
    col = dc.get(d, "#4a9eff"); bg = dc_bg.get(d, "#060f1e")
    st.markdown(f"""
    <div style="background:{bg};border:2px solid {col};border-radius:8px;
                padding:18px 24px;text-align:center;margin-bottom:16px">
        <div style="color:#6a8aaa;font-family:JetBrains Mono,monospace;font-size:9px;
                    letter-spacing:.2em;margin-bottom:6px">TODAY'S VERDICT — Score {intel.composite:.0f}/100</div>
        <div style="color:{col};font-family:Syne,sans-serif;font-size:40px;
                    font-weight:800;line-height:1;margin-bottom:6px">{d}</div>
        <div style="color:{col};font-family:JetBrains Mono,monospace;font-size:11px;
                    opacity:.85">{dc_msg.get(d,'')}</div>
    </div>""", unsafe_allow_html=True)

    # ── CONTRADICTIONS
    if intel.contradictions:
        section_header("⚠ ACTIVE CONTRADICTIONS")
        render_contradictions(intel)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── AI NARRATIVE
    ai = intel.ai_output
    if ai:
        section_header("⚡ AI DECISION SYNTHESIS")
        conf_col = {"HIGH":"#00ff88","MEDIUM":"#ffb300","LOW":"#ff4444"}.get(ai.get("confidence","LOW"), "#4a9eff")

        if ai.get("anomaly_detected") or ai.get("regime_shift_risk"):
            st.markdown(f"""
            <div style="background:#1a0800;border:1px solid #ff884440;border-radius:6px;
                        padding:10px 14px;margin-bottom:8px;color:#ff8844;
                        font-family:JetBrains Mono,monospace;font-size:10px">
                ⚠ ANOMALY: {ai.get("anomaly_description","Regime shift risk detected")}
            </div>""", unsafe_allow_html=True)

        if ai.get("watch_condition"):
            st.markdown(f"""
            <div style="background:#001a0d;border:1px solid #00ff8840;border-radius:6px;
                        padding:10px 14px;margin-bottom:8px;color:#00ff88;
                        font-family:JetBrains Mono,monospace;font-size:10px">
                👁 WATCH TOMORROW: {ai["watch_condition"]}
            </div>""", unsafe_allow_html=True)

        if ai.get("top_opportunity"):
            st.markdown(f"""
            <div style="background:#001030;border:1px solid #4a9eff40;border-radius:6px;
                        padding:10px 14px;margin-bottom:8px;color:#4a9eff;
                        font-family:JetBrains Mono,monospace;font-size:10px">
                🎯 TOP OPPORTUNITY: {ai["top_opportunity"]}
            </div>""", unsafe_allow_html=True)

        cols = st.columns(2)
        for i, (q_label, q_key) in enumerate([
            ("ENVIRONMENT", "q1_environment"),
            ("MONEY FLOW",  "q2_flow"),
            ("KEY RISKS",   "q3_risks"),
            ("OBSERVE",     "q4_observe"),
        ]):
            with cols[i % 2]:
                txt = ai.get(q_key, "")
                if txt:
                    st.markdown(f"""
                    <div style="background:#060f1e;border:1px solid #0f2440;
                                border-radius:6px;padding:10px 14px;margin-bottom:6px">
                        <div style="color:#4a9eff;font-family:JetBrains Mono,monospace;
                                    font-size:8px;letter-spacing:.15em;margin-bottom:4px">{q_label}</div>
                        <div style="color:#b8d4ec;font-family:JetBrains Mono,monospace;
                                    font-size:10px;line-height:1.7">{txt}</div>
                    </div>""", unsafe_allow_html=True)

    # ── TOP SECTORS
    section_header("↻ TOP SECTORS BY RELATIVE STRENGTH")
    for i, s in enumerate(intel.ranked[:5], 1):
        from ui.components.shared import sector_row
        sector_row(s, i, show_lifecycle=True)

    # ── SCORE LOG
    if "score_history" not in st.session_state:
        st.session_state["score_history"] = []
    history = st.session_state["score_history"]
    from datetime import datetime
    now_str = datetime.now().strftime("%d %b %H:%M")
    if not history or history[-1]["score"] != intel.composite:
        history.append({"time": now_str, "score": intel.composite,
                        "decision": intel.decision, "phase": intel.phase})
    st.session_state["score_history"] = history[-30:]


main()
