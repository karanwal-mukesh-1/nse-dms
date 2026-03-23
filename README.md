# NSE Decision Management System (DMS) v3.0

A hedge-fund-grade market intelligence system for individual NSE traders.
Built on Streamlit, yfinance, Groq AI — entirely free to run.

---

## Architecture

```
dms/
├── app.py                          # Streamlit entry point + navigation
├── requirements.txt
│
├── config/
│   └── settings.py                 # ALL configuration: weights, thresholds, symbols
│
├── core/
│   ├── models.py                   # Pydantic models — every data structure
│   └── math_utils.py               # Pure math functions (no I/O, fully testable)
│
├── data/
│   ├── market_data.py              # yfinance: prices, breadth, commodities
│   └── nse_data.py                 # NSE: bulk deals, insider activity, FII/DII
│
├── intelligence/
│   ├── scoring.py                  # Rolling-percentile scores (vol, trend, breadth, etc.)
│   ├── sector_engine.py            # RS ranking, lifecycle, reflexivity, rate cycle
│   ├── opportunity_engine.py       # Stock screener + trade setup generator
│   ├── contradiction_engine.py     # Signal conflict detector
│   ├── ai_engine.py                # Groq structured JSON output
│   └── master_engine.py            # Orchestrator → MarketIntelligence object
│
├── ui/
│   └── components/
│       └── shared.py               # Reusable UI components (no business logic)
│
├── pages/
│   ├── 01_morning_brief.py         # Pre-market checklist (open this every morning)
│   ├── 02_overview.py              # Scores, heatmap, contradictions
│   ├── 03_opportunities.py         # Stock screener + AI top opportunity
│   ├── 04_sectors.py               # Heatmap, rotation, lifecycle, reflexivity, 52W
│   ├── 05_smart_money.py           # Bulk deals, insider activity, clusters
│   ├── 06_macro.py                 # Commodities, rate cycle, FII/DII, PCR
│   ├── 07_watchlist.py             # Custom stock scoring
│   └── 08_history.py               # Score history log
│
└── tests/
    ├── conftest.py                  # Shared fixtures
    ├── test_math_utils.py           # Pure math unit tests
    ├── test_models.py               # Pydantic model tests
    ├── test_scoring.py              # Scoring function tests
    ├── test_sector_engine.py        # Sector intelligence tests
    └── test_nse_data.py             # NSE data classification tests
```

---

## Intelligence Layers

| Layer | What it measures | Data source |
|-------|-----------------|-------------|
| Volatility | India VIX rolling percentile | yfinance |
| Trend | Nifty vs 20/50/200 MA + RSI z-score | yfinance |
| Momentum | RS vs Nifty (not raw % up) | yfinance |
| Breadth | Real % above 50MA from Nifty50 stocks | yfinance |
| Macro | DXY slope rolling percentile | yfinance |
| Smart Money | 5-factor volume proxy (honest labelling) | yfinance |
| Lifecycle | Neglected→Discovered→Consensus→Crowded→Abandoned | yfinance |
| Reflexivity | Soros: price momentum vs fundamental gap | yfinance |
| Bulk Deals | Institutional buy/sell classification | NSE public API |
| Insider Activity | Promoter buy, pledge events, cluster buying | NSE PIT disclosures |
| FII/DII Flow | Provisional daily net flow | NSE API |
| Commodities | Crude, copper, silver, gold — NSE sector spillover | yfinance |
| Rate Cycle | RBI cycle stage → sector playbook | Yield proxy |
| AI Synthesis | Structured JSON: opportunity + risk + watch condition | Groq free tier |

---

## Scoring System

All scores are 0-100. Self-calibrating via rolling percentile (no arbitrary thresholds).

```
Composite = Volatility×20% + Trend×20% + Momentum×20% + 
            Breadth×15% + Macro×10% + SmartMoney×10% + Lifecycle×5%

Decision:
  STRONG YES  → composite ≥ 82 AND conviction ≥ 65
  YES         → composite ≥ 72
  CAUTION     → composite ≥ 58
  NO          → below 58 (DO NOTHING mode)
```

---

## Deployment (Streamlit Community Cloud — free)

### Step 1: GitHub
1. Create repo `nse-dms` (Public)
2. Upload all files preserving directory structure

### Step 2: Streamlit Cloud
1. Go to `share.streamlit.io` → sign in with GitHub
2. New app → select repo → main file: `app.py` → Deploy

### Step 3: Groq API Key (set once, never type again)
1. Get free key at `console.groq.com`
2. In Streamlit Cloud: App Settings → Secrets
3. Add: `GROQ_API_KEY = "gsk_..."`

---

## Running Tests

```bash
cd dms
pip install -r requirements.txt pytest
python -m pytest tests/ -v
```

Expected: ~40 tests, all passing (tests do not make network calls).

---

## Honest Limitations

| Feature | Reality |
|---------|---------|
| Smart Money | Volume proxy only. Not delivery %, OI, or actual flow |
| Breadth | Real Nifty50 breadth when fetch succeeds; sector proxy as fallback |
| Bulk/Insider data | NSE may rate-limit from Streamlit Cloud IPs |
| Data delay | Yahoo Finance = 15-minute delay |
| PCR | Estimated from VIX; true PCR needs NSE options endpoint |
| Reflexivity | Price vs volume-based fundamental proxy; not actual earnings |

---

## The Edge

Hedge funds do not have better NSE data than you.
They have better **organisation** of the same public data.

This system gives you:
- Pre-market decision in 60 seconds (Morning Brief)
- Sector lifecycle classification (Neglected→Discovered transition)
- Reflexivity warning (when price outruns fundamentals)
- Bulk deal + insider confluence with technical signals
- Global commodity spillover mapped to NSE sectors
- Rate cycle playbook for sector positioning
- AI synthesis of all signals into one specific opportunity

**The real edge is systematic execution, not better data.**
