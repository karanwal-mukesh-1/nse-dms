"""
intelligence/ai_engine.py
==========================
Groq LLM integration.
Produces structured AIDecisionOutput — not narrative text.
The AI synthesises ALL intelligence layers into specific, actionable output.
"""

from __future__ import annotations
import json
import requests
import streamlit as st
from typing import Optional, Dict, Any

from core.models import MarketIntelligence, AIDecisionOutput


GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def _build_prompt(intel: MarketIntelligence) -> str:
    """
    Build a rich, structured prompt that feeds ALL intelligence layers.
    The AI acts as a hedge fund analyst synthesising quant signals.
    """
    # Top sectors with RS
    ranked = intel.ranked[:5] if intel.ranked else []
    top3   = ", ".join(
        f"{s.short}(RS:{s.rs_vs_nifty:+.1f}%, {s.sm.signal})"
        for s in ranked[:3]
    )
    bot3   = ", ".join(
        f"{s.short}(RS:{s.rs_vs_nifty:+.1f}%)"
        for s in ranked[-3:]
    ) if len(ranked) >= 3 else "N/A"

    # Contradictions
    contra = "; ".join(c.msg for c in intel.contradictions) if intel.contradictions else "none"

    # Reflexivity warnings
    reflex = "; ".join(
        f"{r.sector}:{r.stage}(gap:{r.gap:+.0f})"
        for r in intel.reflexivity if r.conviction in ("HIGH","MEDIUM")
    ) if intel.reflexivity else "none computed"

    # Lifecycle alerts
    crowded   = [l.sector for l in intel.lifecycles if l.stage == "crowded"]
    neglected = [l.sector for l in intel.lifecycles if l.stage in ("neglected","discovered")]
    lifecycle_note = ""
    if crowded:
        lifecycle_note += f"CROWDED (exit caution): {', '.join(crowded)}. "
    if neglected:
        lifecycle_note += f"NEGLECTED/DISCOVERED (opportunity): {', '.join(neglected)}."

    # Bulk deals
    bulk_str = "none"
    if intel.bulk_deals:
        top_deals = intel.bulk_deals[:3]
        bulk_str  = "; ".join(
            f"{d.symbol} {d.deal_type} by {d.client[:20]} ₹{d.value_cr:.0f}Cr"
            for d in top_deals
        )

    # Insider activity
    insider_str = "none"
    if intel.insider_activity:
        top_ins    = intel.insider_activity[:3]
        insider_str = "; ".join(
            f"{a.symbol}: {a.signal_type} by {a.person[:20]}"
            for a in top_ins
        )

    # Commodities
    comm_alerts = ""
    if intel.commodities:
        movers = [c for c in intel.commodities if abs(c.chg_5d_pct) > 2]
        if movers:
            comm_alerts = "; ".join(
                f"{c.name} {c.chg_5d_pct:+.1f}%5d→{','.join(c.nse_sectors)}"
                for c in movers[:3]
            )

    # Top opportunity
    opp_str = "none screened"
    if intel.opportunities:
        top = intel.opportunities[0]
        opp_str = (
            f"{top.name}({top.sector}) score:{top.score}/100 "
            f"setup:{top.setup_type} conf:{top.confluence}/5 "
            f"{'BULK_BUY' if top.bulk_deal else ''} "
            f"thesis:{top.thesis}"
        )

    # Breadth note
    b_note = (
        f"REAL Nifty50 breadth: {intel.breadth_score:.0f}% above 50MA"
        if intel.breadth_source == "real_nifty50"
        else f"Sector proxy breadth: {intel.breadth_score:.0f}%"
    )

    # VIX
    vix_str = f"{intel.vix_level:.1f} ({intel.vix_pct:.0f}th pct, slope:{intel.vix_slope:+.1f}%)" \
              if intel.vix_level else "N/A"

    return f"""You are a quantitative analyst at a systematic hedge fund specialising in Indian equities.
Your role: synthesise multi-layer market intelligence into specific, actionable output.
Be concrete. Name specific sectors and setups. Avoid generic statements.

=== INTELLIGENCE SNAPSHOT ===
Decision: {intel.decision} | Score: {intel.composite:.0f}/100 | Conviction: {intel.conviction.label}
Phase: {intel.phase} | Nifty 20D: {intel.nifty_r20:+.1f}%
VIX: {vix_str}
{b_note}
RSI(14): {f"{intel.nrsi:.0f}" if intel.nrsi else "N/A"}
Nifty vs 200MA: {f"{intel.n200:+.1f}%" if intel.n200 is not None else "N/A"}

Smart Money Proxy: {intel.sm_signal} (avg score {intel.sm_avg:.0f}/100)
RS Leaders: {top3}
RS Laggards: {bot3}
Contradictions: {contra}
Reflexivity: {reflex}
Lifecycle: {lifecycle_note or "no strong signals"}
Bulk Deals (last 5 days): {bulk_str}
Insider Activity: {insider_str}
Commodity Spillovers: {comm_alerts or "none significant"}
Top Opportunity: {opp_str}

=== REQUIRED JSON OUTPUT ===
Return ONLY valid JSON matching this schema exactly:
{{
  "narrative": "2-3 sentence synthesis of current environment",
  "q1_environment": "1 sentence: what phase, what is driving it",
  "q2_flow": "1 sentence: where is institutional/smart money rotating and why",
  "q3_risks": "1 sentence: the single biggest risk or contradiction right now",
  "q4_observe": "1 sentence: specific condition that would change the picture",
  "top_opportunity": "Specific: SECTOR — STOCK above ₹LEVEL, stop ₹LEVEL, why",
  "stop_condition": "What single event/price would invalidate the current thesis",
  "watch_condition": "One specific thing to monitor at market open tomorrow",
  "anomaly_detected": true or false,
  "anomaly_description": "describe if anomaly, empty string if not",
  "lifecycle_alert": "if any sector transitioning Neglected→Discovered or Crowded→topping, describe it. Else empty.",
  "reflexivity_warning": "if any sector price is far ahead of fundamentals, name it and quantify the gap. Else empty.",
  "confidence": "LOW or MEDIUM or HIGH",
  "regime_shift_risk": true or false
}}"""


def call_groq(api_key: str, intel: MarketIntelligence) -> AIDecisionOutput:
    """
    Call Groq API with full market intelligence.
    Returns structured AIDecisionOutput — every field drives a UI element.
    Falls back gracefully on any error.
    """
    fallback = AIDecisionOutput(
        narrative="Groq analysis unavailable. Check API key in sidebar.",
        confidence="LOW",
    )

    if not api_key:
        return fallback

    try:
        prompt = _build_prompt(intel)

        resp = requests.post(
            GROQ_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model":           GROQ_MODEL,
                "max_tokens":      600,
                "temperature":     0.2,
                "response_format": {"type": "json_object"},
                "messages":        [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )

        data = resp.json()

        if "error" in data:
            fallback.narrative = f"Groq error: {data['error']['message']}"
            return fallback

        raw = data["choices"][0]["message"]["content"]
        parsed = json.loads(raw)

        return AIDecisionOutput(
            narrative=           parsed.get("narrative", ""),
            q1_environment=      parsed.get("q1_environment", ""),
            q2_flow=             parsed.get("q2_flow", ""),
            q3_risks=            parsed.get("q3_risks", ""),
            q4_observe=          parsed.get("q4_observe", ""),
            top_opportunity=     parsed.get("top_opportunity", ""),
            stop_condition=      parsed.get("stop_condition", ""),
            watch_condition=     parsed.get("watch_condition", ""),
            anomaly_detected=    bool(parsed.get("anomaly_detected", False)),
            anomaly_description= parsed.get("anomaly_description", ""),
            lifecycle_alert=     parsed.get("lifecycle_alert", ""),
            reflexivity_warning= parsed.get("reflexivity_warning", ""),
            confidence=          parsed.get("confidence", "LOW"),
            regime_shift_risk=   bool(parsed.get("regime_shift_risk", False)),
        )

    except Exception as e:
        fallback.narrative = f"Request failed: {str(e)}"
        return fallback


def get_groq_key() -> str:
    """
    Retrieve Groq API key.
    Priority: 1) st.secrets (Streamlit Cloud) → 2) session state (manual entry)
    """
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return st.session_state.get("groq_key", "")
