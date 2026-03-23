"""
app.py
======
Entry point for NSE Decision Management System.
Streamlit multipage app — each page is a self-contained module.

Pages:
  1. Morning Brief     — pre-market checklist + AI decision
  2. Overview          — composite scores + decision badge
  3. Opportunities     — stock screener with trade setups
  4. Sectors           — heatmap + rotation + lifecycle
  5. Smart Money       — bulk deals + insider activity + signals
  6. Macro & Global    — commodities + rate cycle + FII/DII
  7. Watchlist         — custom stock scoring
  8. History           — score log + session history
"""

import streamlit as st

# ─── PAGE CONFIG (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title = "NSE Decision Management System",
    page_icon  = "◈",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

# ─── GLOBAL CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Syne:wght@700;800&display=swap');

html, body, [class*="css"] { background-color:#030712; color:#b8d4ec; }
.stApp { background-color:#030712; }
#MainMenu,footer,header { visibility:hidden; }

/* Metric cards */
[data-testid="metric-container"] {
    background:#060f1e; border:1px solid #0f2440; border-radius:8px; padding:12px 16px;
}
[data-testid="metric-container"] label {
    color:#3a5a7f !important; font-family:'JetBrains Mono',monospace !important;
    font-size:9px !important; letter-spacing:.15em !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family:'JetBrains Mono',monospace !important; font-size:18px !important;
}

/* Sidebar */
[data-testid="stSidebar"] { background-color:#060f1e; border-right:1px solid #0f2440; }
[data-testid="stSidebar"] * { color:#b8d4ec; }

/* Navigation */
[data-testid="stSidebarNav"] a { font-family:'JetBrains Mono',monospace; font-size:11px; }
[data-testid="stSidebarNav"] a:hover { background:#0a1628; }

/* Buttons */
.stButton>button {
    background:#060f1e; border:1px solid #4a9eff; color:#4a9eff;
    font-family:'JetBrains Mono',monospace; font-size:11px; border-radius:4px;
}
.stButton>button:hover { background:#0a1628; }

/* Text input */
.stTextInput>div>div>input {
    background:#060f1e; border:1px solid #0f2440;
    color:#e2eef8; font-family:'JetBrains Mono',monospace; font-size:12px;
}

/* Dataframe */
[data-testid="stDataFrame"] { border:1px solid #0f2440; border-radius:8px; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background:#060f1e; border-bottom:1px solid #0f2440; }
.stTabs [data-baseweb="tab"] {
    background:transparent; color:#3a5a7f;
    font-family:'JetBrains Mono',monospace; font-size:9px; letter-spacing:.12em;
}
.stTabs [aria-selected="true"] {
    color:#4a9eff !important; border-bottom:2px solid #4a9eff !important;
    background:transparent !important;
}

/* Expander */
.streamlit-expanderHeader {
    background:#060f1e !important; border:1px solid #0f2440 !important;
    color:#4a9eff !important; font-family:'JetBrains Mono',monospace !important;
    font-size:9px !important; letter-spacing:.15em !important;
}
.streamlit-expanderContent {
    background:#060f1e !important; border:1px solid #0f2440 !important;
    border-top:none !important;
}

/* Selectbox */
.stSelectbox>div>div { background:#060f1e; border:1px solid #0f2440; color:#b8d4ec; }

/* Multiselect */
.stMultiSelect>div>div { background:#060f1e; border:1px solid #0f2440; }
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR: KEY + STATUS ────────────────────────────────────────────────────
from intelligence.ai_engine import get_groq_key
import streamlit as st

with st.sidebar:
    st.markdown("""
    <div style="color:#4a9eff;font-family:Syne,sans-serif;font-size:18px;
                font-weight:800;margin-bottom:2px;">◈ NSE DMS</div>
    <div style="color:#3a5a7f;font-family:'JetBrains Mono',monospace;font-size:8px;
                margin-bottom:16px;letter-spacing:.1em">DECISION MANAGEMENT SYSTEM</div>
    """, unsafe_allow_html=True)

    # Groq key
    st.markdown('<div style="color:#4a9eff;font-family:\'JetBrains Mono\',monospace;font-size:8px;letter-spacing:.15em;margin-bottom:4px;">⚡ GROQ AI</div>', unsafe_allow_html=True)
    secret_key = get_groq_key()
    if secret_key:
        st.markdown('<div style="color:#00ff88;font-family:\'JetBrains Mono\',monospace;font-size:9px;margin-bottom:8px;">● KEY LOADED FROM SECRETS</div>', unsafe_allow_html=True)
    else:
        manual_key = st.text_input(
            "Groq Key", type="password",
            placeholder="gsk_... from console.groq.com",
            label_visibility="collapsed",
            key="groq_key_input",
        )
        if manual_key:
            st.session_state["groq_key"] = manual_key
            st.markdown('<div style="color:#00ff88;font-family:\'JetBrains Mono\',monospace;font-size:9px;">● GROQ ACTIVE</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#3a5a7f;font-family:\'JetBrains Mono\',monospace;font-size:8px;">console.groq.com — free</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Refresh
    from utils.cache_manager import clear_all_cache, cache_status_html

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("↺ REFRESH", use_container_width=True, key="global_refresh"):
            clear_all_cache()
            st.rerun()
    with col_r2:
        if st.button("⚡ REGEN AI", use_container_width=True, key="regen_ai"):
            st.session_state.pop("groq_analysis", None)
            st.rerun()

    st.markdown("---")
    st.markdown(
        cache_status_html(),
        unsafe_allow_html=True,
    )
    st.markdown("""
    <div style="color:#2a4a6f;font-family:'JetBrains Mono',monospace;font-size:8px;
                line-height:1.7;margin-top:8px;">
    Data: Yahoo Finance · NSE India<br>
    AI: Groq llama-3.3-70b (free)<br>
    Delay: 15 min (Yahoo Finance)<br>
    <span style="color:#1e3a5f;">v3.0 — Modular Architecture</span>
    </div>
    """, unsafe_allow_html=True)

# ─── NAVIGATION: PAGES ───────────────────────────────────────────────────────
# Streamlit multipage: pages/ directory is auto-discovered
# Each file in pages/ is a separate page
# app.py = home / landing page

st.markdown("""
<div style="text-align:center;padding:40px 0 20px;">
  <div style="color:#4a9eff;font-family:Syne,sans-serif;font-size:32px;font-weight:800;">
    ◈ NSE Decision Management System
  </div>
  <div style="color:#3a5a7f;font-family:'JetBrains Mono',monospace;font-size:11px;margin-top:8px;letter-spacing:.15em;">
    HEDGE-FUND INTELLIGENCE FOR INDIVIDUAL TRADERS
  </div>
</div>
""", unsafe_allow_html=True)

# Quick nav cards
cols = st.columns(4)
pages = [
    ("☀ Morning Brief",   "pages/01_morning_brief.py",   "Pre-market 5-point checklist + AI decision"),
    ("📊 Overview",        "pages/02_overview.py",        "Scores, phase, conviction, contradictions"),
    ("🎯 Opportunities",   "pages/03_opportunities.py",   "Stock screener with trade setups"),
    ("↻ Sectors",          "pages/04_sectors.py",         "Heatmap, rotation, lifecycle, RS"),
]
for col, (title, path, desc) in zip(cols, pages):
    with col:
        st.markdown(f"""
        <div style="background:#060f1e;border:1px solid #0f2440;border-radius:8px;
                    padding:14px;text-align:center;height:90px;">
            <div style="color:#4a9eff;font-family:'JetBrains Mono',monospace;font-size:12px;
                        font-weight:600;margin-bottom:6px;">{title}</div>
            <div style="color:#3a5a7f;font-family:'JetBrains Mono',monospace;font-size:9px;
                        line-height:1.5;">{desc}</div>
        </div>""", unsafe_allow_html=True)

cols2 = st.columns(4)
pages2 = [
    ("💰 Smart Money",    "pages/05_smart_money.py",   "Bulk deals, insider activity, signals"),
    ("🌐 Macro & Global", "pages/06_macro.py",         "Commodities, rate cycle, FII/DII"),
    ("◎ Watchlist",       "pages/07_watchlist.py",     "Custom stock scoring"),
    ("📈 History",         "pages/08_history.py",       "Score log, session history"),
]
for col, (title, path, desc) in zip(cols2, pages2):
    with col:
        st.markdown(f"""
        <div style="background:#060f1e;border:1px solid #0f2440;border-radius:8px;
                    padding:14px;text-align:center;height:90px;">
            <div style="color:#4a9eff;font-family:'JetBrains Mono',monospace;font-size:12px;
                        font-weight:600;margin-bottom:6px;">{title}</div>
            <div style="color:#3a5a7f;font-family:'JetBrains Mono',monospace;font-size:9px;
                        line-height:1.5;">{desc}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="color:#1e3a5f;font-family:'JetBrains Mono',monospace;font-size:8px;text-align:center;">
Use the left sidebar to navigate between pages · Data is 15-minute delayed ·
Not investment advice · For educational purposes
</div>""", unsafe_allow_html=True)
