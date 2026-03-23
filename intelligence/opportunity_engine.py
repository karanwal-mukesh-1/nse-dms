"""
intelligence/opportunity_engine.py
====================================
Generates specific stock opportunities within top-ranked sectors.
Produces StockOpportunity objects with full scorecards and trade setups.
This is the bridge between "sector is good" and "what do I look at."
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np

from core.models import (
    QuoteData, SectorData, StockOpportunity, SmartMoneyResult,
    BulkDeal, InsiderActivity
)
from core.math_utils import (
    sma, rsi, pct_change, return_n, pct_of_range,
    atr, momentum_score
)
from intelligence.scoring import score_smart_money
from data.market_data import fetch_stock_data


# ─── STOCK SCORER ────────────────────────────────────────────────────────────

def score_stock(symbol: str,
                q: QuoteData,
                sector: SectorData,
                bulk_deals: List[BulkDeal],
                insider_acts: List[InsiderActivity]) -> StockOpportunity:
    """
    Full 10-factor stock scorecard. Returns StockOpportunity.
    Factors (10 pts each = 100 max):
      1. Above 20MA
      2. Above 50MA
      3. Above 200MA
      4. RSI in sweet zone (50-70)
      5. Volume expansion
      6. RS vs sector positive
      7. 52W position < 80% (not extended)
      8. 5D momentum positive
      9. Smart money signal positive
     10. Bulk deal or insider buy in last 5 days
    """
    closes  = q.closes
    volumes = q.volumes
    price   = q.price

    chg_1d   = pct_change(price, q.prev)
    r5       = return_n(closes, 5)
    r20      = return_n(closes, 20)
    m20      = sma(closes, 20)
    m50      = sma(closes, 50)
    m200     = sma(closes, 200)
    nrsi     = rsi(closes)
    vs20     = pct_change(price, m20)  if m20  else None
    vs50     = pct_change(price, m50)  if m50  else None
    vs200    = pct_change(price, m200) if m200 else None
    pos52    = pct_of_range(price, q.l52, q.h52)
    sm       = score_smart_money(q)
    avg_vol  = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else None
    vol_r    = (volumes[-1] / avg_vol) if avg_vol and volumes else None

    # RS vs sector
    rs_vs_sec = r20 - sector.return20d if sector.valid else 0.0

    # Check for recent bulk/insider activity
    sym_clean  = symbol.upper().replace(".NS", "")
    recent_bulk = next(
        (b for b in bulk_deals if sym_clean in b.symbol.upper() and b.deal_type == "BUY"),
        None
    )
    recent_ins = next(
        (a for a in insider_acts if sym_clean in a.symbol.upper() and "BUY" in a.signal_type),
        None
    )

    # Score each factor
    pts = 0
    if vs20  is not None and vs20  > 0: pts += 10
    if vs50  is not None and vs50  > 0: pts += 10
    if vs200 is not None and vs200 > 0: pts += 10
    if nrsi  is not None and 50 < nrsi < 70: pts += 10
    if vol_r is not None and vol_r > 1.2:    pts += 10
    if rs_vs_sec > 0:                         pts += 10
    if pos52 is not None and pos52 < 80:      pts += 10  # not extended
    if r5 > 0:                                pts += 10
    if sm.score > 60:                         pts += 10
    if recent_bulk or recent_ins:             pts += 10

    # Determine setup type
    setup_type  = ""
    watch_level = None
    stop_level  = None
    thesis      = ""

    # ATR for stop levels (approximate)
    atr_val = None
    if len(closes) >= 15:
        highs  = closes   # proxy — true ATR needs high/low
        lows   = closes
        atr_val = float(np.std(closes[-14:])) * 1.5

    if vs20 and vs20 > 0 and vs200 and vs200 > 0 and nrsi and 55 < nrsi < 68:
        setup_type  = "MOMENTUM_CONTINUATION"
        watch_level = round(price * 1.02, 1)     # 2% above current
        stop_level  = round(m20 * 0.99, 1) if m20 else None
        thesis      = f"Above all MAs with RSI {nrsi:.0f} — continuation setup"

    elif vs20 and vs20 > 0 and vs20 < 3 and r5 < 0:
        setup_type  = "PULLBACK_TO_20MA"
        watch_level = round(price * 1.015, 1)
        stop_level  = round(price * 0.97, 1)
        thesis      = "Pulled back to 20MA in uptrend — higher probability entry"

    elif pos52 and pos52 < 25 and sm.score > 65 and r5 > 1:
        setup_type  = "EARLY_RECOVERY"
        watch_level = round(price * 1.03, 1)
        stop_level  = round(price * 0.95, 1)
        thesis      = f"Near 52W low ({pos52:.0f}%) with smart money improving"

    elif recent_bulk and vs50 and vs50 > 0:
        setup_type  = "INSTITUTIONAL_BUY"
        watch_level = round(price * 1.02, 1)
        stop_level  = round(price * 0.96, 1)
        thesis      = f"Institutional bulk buy + above 50MA — {recent_bulk.client[:25]}"

    confluence = sum([
        bool(setup_type),
        bool(recent_bulk or recent_ins),
        sm.score > 65,
        bool(vs200 and vs200 > 0),
        bool(nrsi and 50 < nrsi < 72),
    ])

    name = symbol.replace(".NS", "").replace(".BO", "")

    return StockOpportunity(
        symbol=symbol,
        name=name,
        sector=sector.short,
        price=price,
        score=pts,
        chg_1d=round(chg_1d, 2),
        return_5d=round(r5, 2),
        return_20d=round(r20, 2),
        vs_20ma=round(vs20, 2) if vs20 is not None else None,
        vs_50ma=round(vs50, 2) if vs50 is not None else None,
        vs_200ma=round(vs200, 2) if vs200 is not None else None,
        rsi=round(nrsi, 1) if nrsi else None,
        vol_ratio=round(vol_r, 2) if vol_r else None,
        pos_52w=pos52,
        rs_vs_sector=round(rs_vs_sec, 2),
        smart_money=sm,
        bulk_deal=recent_bulk,
        insider=recent_ins,
        setup_type=setup_type,
        watch_level=watch_level,
        stop_level=stop_level,
        confluence=confluence,
        thesis=thesis,
    )


# ─── OPPORTUNITY SCREENER ────────────────────────────────────────────────────

def screen_opportunities(
    top_sectors:    List[SectorData],
    quotes:         Dict[str, QuoteData],
    bulk_deals:     List[BulkDeal],
    insider_acts:   List[InsiderActivity],
    max_per_sector: int = 3,
    min_score:      int = 50,
) -> List[StockOpportunity]:
    """
    Screen stocks in top sectors for opportunities.
    Fetches individual stock data, scores each, returns ranked list.

    Only runs for top 3 sectors by RS to keep fetch time manageable.
    """
    all_opps: List[StockOpportunity] = []

    for sector in top_sectors[:3]:
        if not sector.valid or not sector.stocks:
            continue

        # Fetch stock data
        stock_quotes = fetch_stock_data(tuple(sector.stocks))

        sector_opps = []
        for sym in sector.stocks:
            q = stock_quotes.get(sym)
            if not q or not q.loaded or len(q.closes) < 20:
                continue

            opp = score_stock(sym, q, sector, bulk_deals, insider_acts)

            if opp.score >= min_score or opp.bulk_deal or opp.insider:
                sector_opps.append(opp)

        # Sort by score, take top N per sector
        sector_opps.sort(key=lambda x: x.score, reverse=True)
        all_opps.extend(sector_opps[:max_per_sector])

    # Final sort: score + confluence + bulk deal bonus
    def rank_key(o):
        bonus = 15 if o.bulk_deal else 0
        bonus += 10 if o.insider  else 0
        return o.score + bonus + o.confluence * 5

    all_opps.sort(key=rank_key, reverse=True)
    return all_opps[:10]  # top 10 opportunities max
