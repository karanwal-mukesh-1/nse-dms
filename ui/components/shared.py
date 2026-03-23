"""
ui/components/shared.py
========================
Reusable UI components. Every page imports from here.
No business logic — pure rendering only.
"""

from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
from typing import Optional, List, Dict, Any

from core.models import (
    MarketIntelligence, SectorData, StockOpportunity,
    BulkDeal, InsiderActivity, SmartMoneyResult
)
from config.settings import (
    COLORS, SM_SIGNAL_COLORS, DECISION_COLORS, PHASE_COLORS
)


# ─── TYPOGRAPHY HELPERS ───────────────────────────────────────────────────────

def section_header(text: str, icon: str = ""):
    st.markdown(
        f'<div style="color:#4a9eff;font-family:JetBrains Mono,monospace;font-size:9px;'
        f'letter-spacing:.2em;border-bottom:1px solid #0f2440;padding-bottom:5px;'
        f'margin-bottom:10px;margin-top:4px;">{icon} {text}</div>',
        unsafe_allow_html=True,
    )


def mono(text: str, color: str = "#b8d4ec", size: int = 11) -> str:
    return f'<span style="color:{color};font-family:JetBrains Mono,monospace;font-size:{size}px">{text}</span>'


def score_color(s: float) -> str:
    return COLORS["green"] if s >= 75 else COLORS["amber"] if s >= 55 else COLORS["red"]


def fmt(v: Optional[float], d: int = 1, plus: bool = False) -> str:
    if v is None:
        return "---"
    return (("+" if plus and v > 0 else "") + f"{v:.{d}f}")


def sm_tag(signal: str, small: bool = False) -> str:
    col = SM_SIGNAL_COLORS.get(signal, "#4a6a8a")
    sz  = 8 if small else 9
    return (
        f'<span style="background:{col}20;border:1px solid {col}50;color:{col};'
        f'font-family:JetBrains Mono,monospace;font-size:{sz}px;'
        f'padding:2px 6px;border-radius:3px;white-space:nowrap">{signal}</span>'
    )


def conviction_dots(score: float, phase: str) -> str:
    col   = PHASE_COLORS.get(phase, "#4a9eff")
    filled = round(score / 20)
    dots  = "".join(
        f'<span style="color:{col if i < filled else "#1e3a5f"};font-size:12px">●</span>'
        for i in range(5)
    )
    return dots


# ─── PLOTLY THEME ────────────────────────────────────────────────────────────

PLOTLY_THEME = dict(
    paper_bgcolor="#030712",
    plot_bgcolor="#060f1e",
    font=dict(family="JetBrains Mono", color="#b8d4ec", size=10),
    margin=dict(l=8, r=8, t=32, b=8),
    xaxis=dict(showgrid=False, color="#3a5a7f", tickfont=dict(size=9)),
    yaxis=dict(showgrid=True, gridcolor="#0f2440", color="#3a5a7f", tickfont=dict(size=9)),
)


# ─── DECISION BADGE ───────────────────────────────────────────────────────────

def render_decision_badge(intel: MarketIntelligence):
    dc = DECISION_COLORS.get(intel.decision, DECISION_COLORS["NO"])
    pc = PHASE_COLORS.get(intel.phase, "#4a9eff")
    dots = conviction_dots(intel.conviction.score, intel.phase)

    st.markdown(f"""
    <div style="background:{dc['bg']};border:2px solid {dc['border']};border-radius:10px;
                padding:20px;text-align:center;">
        <div style="color:#6a8aaa;font-family:JetBrains Mono,monospace;font-size:8px;
                    letter-spacing:.2em;margin-bottom:6px;">MARKET ENVIRONMENT</div>
        <div style="color:{dc['color']};font-family:Syne,sans-serif;
                    font-size:{42 if intel.decision=='STRONG YES' else 52}px;
                    font-weight:800;line-height:1;">{intel.decision}</div>
        <div style="color:{pc};font-family:JetBrains Mono,monospace;
                    font-size:10px;margin-top:6px;letter-spacing:.1em;">{intel.phase}</div>
        <div style="margin:8px 0 4px">{dots}</div>
        <div style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px;">
            {intel.conviction.label} CONVICTION · {intel.composite:.0f}/100
        </div>
    </div>""", unsafe_allow_html=True)


# ─── SCORE RING ───────────────────────────────────────────────────────────────

def score_ring(score: float, label: str, size: int = 100, key_suffix: str = "") -> go.Figure:
    r    = size / 2 - 9
    circ = 3.14159 * 2 * r
    dash = score / 100 * circ
    col  = score_color(score)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="text",
        text=[f"<b>{score:.0f}</b>"],
        textfont=dict(size=size // 4.5, color=col, family="JetBrains Mono"),
        hoverinfo="skip",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False, range=[-1, 1]),
        yaxis=dict(visible=False, range=[-1, 1]),
        width=size, height=size,
        margin=dict(l=0, r=0, t=0, b=0),
        annotations=[dict(
            text=f"<b>{score:.0f}</b>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=size // 4, color=col, family="JetBrains Mono"),
            xref="paper", yref="paper",
        )],
    )
    return fig


# ─── SCORE BARS ──────────────────────────────────────────────────────────────

def render_score_bars(intel: MarketIntelligence):
    bars = [
        ("VOLATILITY",  intel.vol_score,      0.20),
        ("TREND",       intel.trend_score,    0.20),
        ("MOMENTUM",    intel.mom_score,      0.20),
        ("BREADTH",     intel.breadth_score,  0.15),
        ("MACRO",       intel.macro_score,    0.10),
        ("SMART MONEY", intel.sm_score,       0.10),
        ("LIFECYCLE",   intel.lifecycle_bonus,0.05),
    ]
    for label, s, w in bars:
        col = score_color(s)
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(
                f'<div style="color:#3a5a7f;font-family:JetBrains Mono,monospace;'
                f'font-size:9px;margin-bottom:2px">{label} '
                f'<span style="color:#4a9eff">({int(w*100)}%)</span></div>',
                unsafe_allow_html=True,
            )
            st.progress(min(1.0, s / 100))
        with c2:
            st.markdown(
                f'<div style="color:{col};font-family:JetBrains Mono,monospace;'
                f'font-size:11px;padding-top:16px">{s:.0f}/100</div>',
                unsafe_allow_html=True,
            )


# ─── CONTRADICTION PANEL ──────────────────────────────────────────────────────

def render_contradictions(intel: MarketIntelligence):
    if not intel.contradictions:
        st.markdown(
            '<div style="color:#00ff88;font-family:JetBrains Mono,monospace;font-size:10px;">'
            '✓ No contradictions — signals aligned</div>',
            unsafe_allow_html=True,
        )
        return
    for c in intel.contradictions:
        col = "#ff4444" if c.severity == "danger" else "#ffb300" if c.severity == "warn" else "#4a9eff"
        icon = "✗" if c.severity == "danger" else "⚠" if c.severity == "warn" else "ℹ"
        st.markdown(
            f'<div style="color:{col};font-family:JetBrains Mono,monospace;'
            f'font-size:10px;margin-bottom:4px;line-height:1.5">{icon} {c.msg}</div>',
            unsafe_allow_html=True,
        )


# ─── SECTOR ROW ──────────────────────────────────────────────────────────────

def sector_row(s: SectorData, rank: int, show_lifecycle: bool = False):
    rs_col  = "#00ff88" if s.rs_vs_nifty > 0 else "#ff4444"
    chg_col = "#00ff88" if s.chg >= 0 else "#ff4444"
    lc_info = ""
    if show_lifecycle and s.lifecycle:
        from config.settings import LIFECYCLE_STAGES
        lc_col = LIFECYCLE_STAGES.get(s.lifecycle, {}).get("color", "#4a6a8a")
        lc_info = f'<span style="color:{lc_col};font-family:JetBrains Mono,monospace;font-size:8px;margin-left:8px">{s.lifecycle.upper()}</span>'

    st.markdown(f"""
    <div style="background:#060f1e;border:1px solid #0f2440;border-radius:6px;
                padding:8px 14px;margin-bottom:3px;display:flex;
                align-items:center;justify-content:space-between">
        <div style="display:flex;align-items:center;gap:10px">
            <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;
                         font-size:10px;min-width:20px">{rank}.</span>
            <span style="color:#e2eef8;font-family:JetBrains Mono,monospace;
                         font-size:12px;font-weight:600;min-width:52px">{s.short}</span>
            <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;
                         font-size:9px">{s.name}</span>
            {lc_info}
        </div>
        <div style="display:flex;align-items:center;gap:14px">
            <span style="color:{chg_col};font-family:JetBrains Mono,monospace;
                         font-size:10px">1D: {s.chg:+.2f}%</span>
            <span style="color:{rs_col};font-family:JetBrains Mono,monospace;
                         font-size:10px">RS: {s.rs_vs_nifty:+.1f}%</span>
            {sm_tag(s.sm.signal)}
        </div>
    </div>""", unsafe_allow_html=True)


# ─── OPPORTUNITY CARD ─────────────────────────────────────────────────────────

def render_opportunity_card(opp: StockOpportunity, rank: int = 0):
    sc_col  = score_color(opp.score)
    chg_col = "#00ff88" if opp.chg_1d >= 0 else "#ff4444"
    sm_col  = SM_SIGNAL_COLORS.get(opp.smart_money.signal, "#4a6a8a")

    # Badges
    badges = ""
    if opp.bulk_deal:
        badges += f'<span style="background:#001a0d;border:1px solid #00ff8840;color:#00ff88;font-family:JetBrains Mono,monospace;font-size:8px;padding:1px 6px;border-radius:3px;margin-right:4px">BULK BUY</span>'
    if opp.insider:
        badges += f'<span style="background:#001030;border:1px solid #4a9eff40;color:#4a9eff;font-family:JetBrains Mono,monospace;font-size:8px;padding:1px 6px;border-radius:3px;margin-right:4px">INSIDER BUY</span>'

    # Trade setup
    setup_html = ""
    if opp.setup_type:
        setup_html = f"""
        <div style="background:#0a1628;border:1px solid #0f2440;border-radius:4px;
                    padding:6px 10px;margin-top:7px;display:flex;justify-content:space-between;
                    align-items:center">
            <span style="color:#4a9eff;font-family:JetBrains Mono,monospace;font-size:9px">
                {opp.setup_type}</span>
            <div style="display:flex;gap:12px">
                {f'<span style="color:#00ff88;font-family:JetBrains Mono,monospace;font-size:9px">WATCH ₹{opp.watch_level:.0f}</span>' if opp.watch_level else ''}
                {f'<span style="color:#ff4444;font-family:JetBrains Mono,monospace;font-size:9px">STOP ₹{opp.stop_level:.0f}</span>' if opp.stop_level else ''}
                <span style="color:#4a6a8a;font-family:JetBrains Mono,monospace;font-size:9px">
                    {opp.confluence}/5 factors</span>
            </div>
        </div>"""

    st.markdown(f"""
    <div style="background:#060f1e;border:1px solid #0f2440;border-radius:8px;
                padding:14px;margin-bottom:8px">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
            <div style="display:flex;align-items:center;gap:10px">
                {f'<span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:10px">{rank}.</span>' if rank else ''}
                <span style="color:#e2eef8;font-family:JetBrains Mono,monospace;
                             font-size:14px;font-weight:700">{opp.name}</span>
                <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;
                             font-size:9px">{opp.sector}</span>
                <span style="color:{chg_col};font-family:JetBrains Mono,monospace;
                             font-size:10px">{opp.chg_1d:+.2f}% today</span>
                {badges}
            </div>
            <div style="display:flex;align-items:center;gap:8px">
                <span style="background:{sc_col}20;border:1px solid {sc_col}60;color:{sc_col};
                             font-family:JetBrains Mono,monospace;font-size:10px;
                             padding:2px 8px;border-radius:3px">{opp.score}/100</span>
                {sm_tag(opp.smart_money.signal)}
            </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-bottom:6px">
            {_metric_cell("5D", opp.return_5d, "%", signed=True)}
            {_metric_cell("20D", opp.return_20d, "%", signed=True)}
            {_metric_cell("vs 20MA", opp.vs_20ma, "%", signed=True)}
            {_metric_cell("RSI", opp.rsi, "", rsi_mode=True)}
            {_metric_cell("Vol", opp.vol_ratio, "x", threshold=1.2)}
            {_metric_cell("52W Pos", opp.pos_52w, "%")}
        </div>
        {f'<div style="color:#b8d4ec;font-family:JetBrains Mono,monospace;font-size:10px;margin-top:4px">{opp.thesis}</div>' if opp.thesis else ''}
        {setup_html}
    </div>""", unsafe_allow_html=True)


def _metric_cell(label: str, val: Optional[float], unit: str,
                  signed: bool = False, threshold: float = 0,
                  rsi_mode: bool = False) -> str:
    if val is None:
        col = "#3a5a7f"
        txt = "N/A"
    elif rsi_mode:
        col = "#00ff88" if 50 < val < 70 else "#ffb300" if val >= 70 else "#ff4444"
        txt = f"{val:.0f}"
    elif signed or threshold:
        col = "#00ff88" if (val > threshold) else "#ff4444"
        txt = f"{val:+.1f}{unit}" if signed else f"{val:.1f}{unit}"
    else:
        col = "#00ff88" if val > 50 else "#4a9eff"
        txt = f"{val:.0f}{unit}"

    return f"""<div style="background:#0a1628;border-radius:4px;padding:6px;text-align:center">
        <div style="color:#3a5a7f;font-size:8px;font-family:JetBrains Mono,monospace;
                    margin-bottom:2px">{label}</div>
        <div style="color:{col};font-size:11px;font-family:JetBrains Mono,monospace;
                    font-weight:600">{txt}</div>
    </div>"""


# ─── BULK DEAL ROW ────────────────────────────────────────────────────────────

def render_bulk_deal_row(deal: BulkDeal):
    type_col = "#00ff88" if deal.deal_type == "BUY" else "#ff4444"
    conv_col = {3: "#00ff88", 2: "#ffb300", 1: "#4a9eff", 0: "#3a5a7f"}.get(deal.conviction, "#3a5a7f")

    signal_bg  = "#001a0d" if "BUY" in deal.signal_type else "#1a0000"
    signal_col = "#00ff88" if "BUY" in deal.signal_type else "#ff4444"

    st.markdown(f"""
    <div style="background:#060f1e;border:1px solid #0f2440;border-radius:6px;
                padding:9px 14px;margin-bottom:4px">
        <div style="display:flex;align-items:center;justify-content:space-between">
            <div style="display:flex;align-items:center;gap:10px">
                <span style="color:{type_col};font-family:JetBrains Mono,monospace;
                             font-size:10px;font-weight:700;min-width:30px">{deal.deal_type}</span>
                <span style="color:#e2eef8;font-family:JetBrains Mono,monospace;
                             font-size:12px;font-weight:600">{deal.symbol}</span>
                <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;
                             font-size:9px">{deal.client[:30]}</span>
            </div>
            <div style="display:flex;align-items:center;gap:10px">
                <span style="color:#b8d4ec;font-family:JetBrains Mono,monospace;
                             font-size:10px">₹{deal.value_cr:.0f} Cr</span>
                <span style="background:{signal_bg};border:1px solid {signal_col}40;
                             color:{signal_col};font-family:JetBrains Mono,monospace;
                             font-size:8px;padding:1px 6px;border-radius:3px">
                    {deal.signal_type}</span>
                <span style="color:{conv_col};font-family:JetBrains Mono,monospace;
                             font-size:9px">{'★' * deal.conviction}</span>
            </div>
        </div>
        {f'<div style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:9px;margin-top:4px">{deal.sector or "sector unknown"} · {deal.date}</div>' if deal.date else ''}
    </div>""", unsafe_allow_html=True)


# ─── INSIDER ROW ──────────────────────────────────────────────────────────────

def render_insider_row(act: InsiderActivity):
    signal_colors = {
        "PROMOTER_BUY_NEAR_LOW": ("#00ff88", "#001a0d"),
        "PROMOTER_BUY":          ("#44ff88", "#001a0d"),
        "INSIDER_BUY":           ("#4a9eff", "#001030"),
        "PLEDGE_REVOKED":        ("#00cc55", "#001a0d"),
        "PLEDGE_INVOKED":        ("#ff4444", "#1a0000"),
        "PROMOTER_SELL":         ("#ff8844", "#1a0800"),
        "INSIDER_SELL":          ("#ff4444", "#1a0000"),
    }
    col, bg = signal_colors.get(act.signal_type, ("#4a6a8a", "#0a1a2a"))

    val_str = f"₹{act.value_cr:.2f} Cr" if act.value_cr else ""
    st.markdown(f"""
    <div style="background:#060f1e;border:1px solid #0f2440;border-radius:6px;
                padding:9px 14px;margin-bottom:4px">
        <div style="display:flex;align-items:center;justify-content:space-between">
            <div style="display:flex;align-items:center;gap:10px">
                <span style="color:#e2eef8;font-family:JetBrains Mono,monospace;
                             font-size:12px;font-weight:600">{act.symbol}</span>
                <span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;
                             font-size:9px">{act.person[:25]}</span>
                <span style="color:#4a6a8a;font-family:JetBrains Mono,monospace;
                             font-size:8px">{act.designation[:20]}</span>
            </div>
            <div style="display:flex;align-items:center;gap:10px">
                {f'<span style="color:#b8d4ec;font-family:JetBrains Mono,monospace;font-size:10px">{val_str}</span>' if val_str else ''}
                <span style="background:{bg};border:1px solid {col}40;color:{col};
                             font-family:JetBrains Mono,monospace;font-size:8px;
                             padding:1px 6px;border-radius:3px">{act.signal_type}</span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)


# ─── HEATMAP CHART ────────────────────────────────────────────────────────────

def chart_sector_heatmap(sectors: List[SectorData], timeframe: str = "1D") -> go.Figure:
    tf_map = {
        "1D":  ("chg",       "Daily %"),
        "5D":  ("return5d",  "5-Day %"),
        "1M":  ("return20d", "20-Day %"),
        "3M":  ("return60d", "60-Day %"),
    }
    field, label = tf_map.get(timeframe, ("chg", "Daily %"))
    valid = [s for s in sectors if s.valid]
    if not valid:
        return go.Figure()

    names  = [s.short for s in valid]
    values = [round(getattr(s, field, 0), 2) for s in valid]

    cols = 5
    rows = -(-len(names) // cols)
    while len(names) < rows * cols:
        names.append(""); values.append(None)

    z_grid, t_grid = [], []
    for r in range(rows):
        z_row, t_row = [], []
        for c in range(cols):
            idx = r * cols + c
            v   = values[idx] if idx < len(values) else None
            nm  = names[idx]  if idx < len(names)  else ""
            z_row.append(v if v is not None else 0)
            t_row.append(f"<b>{nm}</b><br>{v:+.2f}%" if v is not None and nm else "")
        z_grid.append(z_row)
        t_grid.append(t_row)

    abs_max = max((abs(v) for v in values if v is not None), default=1)

    fig = go.Figure(go.Heatmap(
        z=z_grid, text=t_grid,
        texttemplate="%{text}",
        textfont=dict(family="JetBrains Mono", size=11, color="white"),
        colorscale=[
            [0.0, "#7f0000"], [0.2, "#cc2222"], [0.4, "#ff4444"],
            [0.45,"#1a0505"], [0.5, "#0a1628"], [0.55,"#052010"],
            [0.6, "#00aa55"], [0.8, "#00cc66"], [1.0, "#00ff88"],
        ],
        zmid=0, zmin=-abs_max, zmax=abs_max,
        showscale=True,
        colorbar=dict(
            title=dict(text=label, font=dict(size=9, color="#4a9eff", family="JetBrains Mono")),
            tickfont=dict(size=8, color="#4a6a8a"),
            thickness=10, len=0.8,
        ),
        xgap=3, ygap=3,
        hovertemplate="<b>%{text}</b><extra></extra>",
    ))
    fig.update_layout(
        **{k: v for k, v in PLOTLY_THEME.items() if k not in ("xaxis","yaxis")},
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(showticklabels=False, showgrid=False),
        height=200,
        title=dict(text=f"Sector Heatmap — {label}",
                   font=dict(size=10, color="#4a9eff", family="JetBrains Mono"), x=0),
        margin=dict(l=8, r=60, t=36, b=8),
    )
    return fig


# ─── NIFTY MA CHART ───────────────────────────────────────────────────────────

def chart_nifty_ma(closes: List[float]) -> go.Figure:
    import numpy as np
    if len(closes) < 50:
        return go.Figure()
    c = closes[-200:]
    x = list(range(len(c)))
    ma20  = [float(np.mean(c[max(0,i-19):i+1])) for i in range(len(c))]
    ma50  = [float(np.mean(c[max(0,i-49):i+1])) if i >= 49  else None for i in range(len(c))]
    ma200 = [float(np.mean(c[max(0,i-199):i+1])) if i >= 199 else None for i in range(len(c))]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=c,    name="Nifty",  line=dict(color="#4a9eff", width=2)))
    fig.add_trace(go.Scatter(x=x, y=ma20, name="20 MA",  line=dict(color="#00ff88", width=1.2, dash="dot")))
    fig.add_trace(go.Scatter(x=x, y=ma50, name="50 MA",  line=dict(color="#ffb300", width=1.2, dash="dot")))
    fig.add_trace(go.Scatter(x=x, y=ma200,name="200 MA", line=dict(color="#ff4444", width=1.5)))
    fig.update_layout(
        **PLOTLY_THEME,
        title=dict(text="Nifty 50 — Price vs Moving Averages",
                   font=dict(size=10, color="#4a9eff"), x=0),
        height=300, showlegend=True,
        legend=dict(orientation="h", x=0, y=1.1, font=dict(size=8)),
    )
    return fig
