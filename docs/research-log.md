# Research Log

Running log of discretionary market/macro research to support backtest and strategy review. Entries are append-only — do not edit or delete prior entries.

---

## 2026-08-16 — BTCUSDT (Bitcoin/USDT)

**Context:** Requested as background situational awareness for stock-soup's first real backtest validation run. Not a trade recommendation, not a backtest, not a gate on results.

### Price level and recent trend (factual)

- Current price: ~$63,010 as of Aug 16, 2026 3:45am EDT (CoinDesk via search). Aug 14 close ~$62,829–$62,822. Aug 7 ~$64,745. 24h volume on Aug 16 reported at only ~$3.47B — thin for BTC, consistent with summer/pre-FOMC liquidity lull.
- Cycle high: ~$126,209 in October 2025. BTC entered 2026 above $93,000. From the Oct 2025 high to the current ~$63k level, BTC is down roughly 50%.
- 2026 YTD has been a grinding downtrend — described consistently across sources as "trapped sideways" / struggling to reclaim moving averages, not a sharp crash but a slow bleed with periodic dead-cat bounces (e.g., the Aug 7 → Aug 14 pullback from ~$64.7k to ~$62.8k).
- Consensus resistance band: $65,000–$70,000. Multiple sources (independent AI/analyst reads cited in press) flag this zone as the level BTC needs to reclaim to invalidate the current downtrend.
- Psychological/round-number support: $60,000. No confirmed break below it as of this log entry, but price is close enough (~5% away) that it's a near-term relevant level.

Confidence note: price/trend figures sourced from secondary press aggregation (Fortune, CoinDesk snippets, crypto news sites) via web search, not a live exchange feed or raw OHLC series. Good enough for macro context, not precise enough for exact intrabar levels.

### Macro drivers (factual)

- **Fed policy:** Rates held at 3.50%–3.75% at the last decision. No FOMC meeting in August — next decision **September 16, 2026**. This means August specifically has a monetary-policy vacuum: thinner summer liquidity, fewer scheduled catalysts, and therefore (per multiple sources) more vulnerable/choppier price action than a normal month.
- **ETF flows:** Cumulative BTC spot ETF inflows since launch ~$51.36B (still net-positive lifetime), but flow momentum has soured recently — record ~$4.51B in outflows in June 2026, July saw intermittent inflows that failed to hold, turning net negative again by month-end. Flow trend is currently a headwind, not a tailwind.
- **Regulatory:** The CLARITY Act (US crypto market-structure bill) has been delayed; Senate vote now expected **September 15, 2026**. Passage odds have reportedly collapsed from ~80% earlier in 2026 to ~20% now amid partisan disagreement. A White House meeting with crypto executives (Coinbase, Ripple, Gemini, Robinhood) plus CFTC Chair Selig, SEC Chair Atkins, Treasury Sec. Bessent, and Commerce Sec. Lutnick was reported as imminent this week (~Aug 17–20), followed by a CFTC advisory committee meeting the following Thursday. Analysts quoted are skeptical this produces an immediate price catalyst — framed as a longer-term de-risking event for institutional adoption, not a near-term trigger.
- **Other:** EU's 20th sanctions package (enforcement deadline May 2026) pushed exchanges including Binance to block transactions with HTX and ~10 other non-compliant platforms — a fragmentation/liquidity-segmentation event for global crypto exchange flow, not specific to BTC price but relevant to cross-exchange liquidity conditions.

### Discretionary Elliott Wave read (subjective — separate from and less certain than any codebase output)

This is my own discretionary count based on secondary price-level reporting, not a full OHLC chart review, and it is **not** the codebase's mechanical `elliott_wave.py` pivot detector — that strategy may produce a different count from mine, and that disagreement is expected, not a bug in either.

**Primary interpretation:** Treating the Oct 2025 high (~$126,209) as the top of the prior bull impulse, the ~10-month, ~50% decline into the current ~$63k level reads most naturally as a large-degree corrective/impulsive decline (Wave A of a broader correction, or an early-stage bear impulse) rather than a normal 4th-wave pullback within an intact bull trend. The depth (50%) and duration (10 months without a clear reversal signal) are large for a typical wave-4 correction in a still-bullish structure, though not impossible if the base of the prior bull move was low enough (see alternate below). Current price action — chopping in the $60k–$65k band with weak volume — reads as either late-stage wave 5 down of that decline, or an early corrective bounce (wave 2/B) that has not yet cleared the $65k–$70k resistance band needed to call the downtrend broken.

**Alternate interpretation:** If the broader bull structure is measured from the 2022 cycle low (~$15.5k) to the Oct 2025 high (~$126k), the current pullback to ~$63k sits roughly in the 45–55% retracement zone of that larger move — a textbook (if deep) Wave 4 correction, with a Wave 5 push toward new highs still structurally possible if $60k holds as support. I don't have high confidence in this alternate; it depends on where you draw the wave-1 origin, and the flow/regulatory backdrop right now doesn't offer strong confirming evidence either way.

**I hold low-to-medium confidence in either count.** The data behind this read is a handful of daily closes from press aggregation, not a full pivot-by-pivot chart study — treat this as a discretionary sanity-check overlay, not a validated wave count.

**Key levels (discretionary, for context only):**
- Invalidation of the bearish/corrective primary count: sustained reclaim above ~$70,000.
- Invalidation of the bullish alternate (wave 4) count: sustained close below ~$60,000, which would open room toward the next round-number/prior-structure support in the $50k–$55k area.
- Near-term resistance: $65,000–$70,000 (also flagged independently by press-cited analyst consensus, not just my own read).
- Near-term support: $60,000 psychological level.

### What the mechanical strategies structurally can't see right now

- **Liquidity/seasonality gap:** No FOMC meeting until Sept 16 — August trades in a monetary-policy vacuum with thinner summer volume (24h volume ~$3.47B reported on Aug 16, on the low side for BTC). Backtested rules calibrated on normal-liquidity regimes may behave differently (wider slippage, more false breakouts) in this specific low-liquidity window.
- **Binary regulatory catalyst risk:** CLARITY Act Senate vote (Sept 15) and the White House crypto-executive meeting (~Aug 17–20) plus CFTC advisory meeting are scheduled, headline-risk events that can move price sharply and are entirely invisible to price-only mechanical strategies. Passage-odds collapse from 80% to 20% is itself a sentiment/positioning fact worth knowing before trusting any backtested edge through mid-September.
- **ETF flow deterioration:** Spot ETF flows have gone from record outflows (June) to failed-to-hold inflows (July) to net negative again — a structural demand-side headwind that a purely price-based backtest wouldn't isolate as a causal factor, but which likely underlies some of the recent downward drift.
- **Exchange fragmentation:** EU sanctions-driven blocking of HTX and other platforms by Binance and peers is a cross-exchange liquidity/fragmentation event that could affect fill quality or basis behavior on some venues, independent of anything visible in a single-exchange price series.

**Net take for backtest validation purposes:** This is not an extreme-volatility or obviously "unsafe" environment (no active crash, no major hack/exploit reported), but it is a **thin-liquidity, event-adjacent chop regime** — sideways/range-bound near multi-month lows, with two scheduled binary catalysts (White House meeting this week, CLARITY Act vote Sept 15, FOMC Sept 16) sitting just ahead. A strategy backtested over the trailing 1-3 months is largely backtested over exactly this low-liquidity, no-major-catalyst chop — results should be treated as reflecting a range-bound, low-momentum regime, not necessarily representative of how the same rules perform in a trending or high-volatility market.
