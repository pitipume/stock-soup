# VI Scoring System

## Philosophy

We combine Warren Buffett's value framework with Peter Lynch's growth criteria.
The goal is not just "cheap stocks" — it's finding companies that are cheap AND
growing AND financially healthy. That combination is rarer and more valuable.

---

## Scoring criteria

Each criterion scores independently. If yfinance has no data for a field, that
criterion is skipped (doesn't penalize the score). This prevents data gaps from
unfairly punishing stocks.

| Criterion | Threshold | Points | Rationale |
|-----------|-----------|--------|-----------|
| P/E ratio | 0 < P/E < 15 | 15 | Cheap relative to earnings. < 0 = losses, excluded. |
| P/B ratio | < 1.5 | 15 | Trading near or below book value — asset-backed |
| Debt/Equity | < 50* | 15 | Not over-leveraged. Room to survive downturns. |
| ROE | > 15% | 15 | Peter Lynch threshold for management quality |
| Revenue growth | > 10% YoY | 15 | Growth company, not a value trap |
| Free cash flow | Positive | 15 | Real earnings, not accounting manipulation |
| Insider ownership | > 5% | 10 | Management has skin in the game |

*yfinance returns D/E in percentage form: 50 = 0.5 ratio (debt is 50% of equity)

**Max score without bonus: 100 points**

---

## Hidden gem bonus (+5 points, capped at 100)

A stock gets the hidden gem bonus if BOTH:
- Market cap < $2 billion (mid/small cap — institutions haven't piled in yet)
- Analyst coverage < 5 firms (underfollowed = potentially mispriced)

This is the "Peter Lynch effect" — finding stocks before Wall Street notices.

---

## Verdict thresholds

| Score | Verdict | Meaning |
|-------|---------|---------|
| ≥ 75 | Strong Buy | Passes most criteria strongly. High conviction. |
| ≥ 55 | Buy | Solid fundamentals. Worth investigating. |
| ≥ 35 | Hold | Mixed signals. Not a buy, not a clear skip. |
| < 35 | Skip | Too many red flags. Not returned in results. |

---

## Known limitation: Yahoo Finance rate limiting

Yahoo Finance (used by yfinance) rate-limits requests aggressively, especially from containerized/cloud environments. The screener uses:
- A browser-like User-Agent session header to reduce rejections
- 1-second delay between every ticker fetch
- Auto-retry with backoff on 429 errors (2 retries, 5s/10s wait)

**Practical effect:** First scan after Docker startup often hits more 429s than subsequent scans (no session warmup). Results may be incomplete on the first run. Restart the scan if you see many rate-limit failures in worker logs.

**Long-term fix (Phase 3):** Cache fundamental data in the DB and only re-fetch tickers where data is stale (> 24h). This reduces Yahoo Finance calls from 500/scan to ~20/scan for unchanged tickers.

---

## Data source: yfinance

yfinance wraps Yahoo Finance's unofficial API. It's free, requires no API key,
and has good coverage of US stocks (S&P 500 + NASDAQ-100).

**Important yfinance value formats:**
- `returnOnEquity`: decimal (0.15 = 15%) ✓
- `revenueGrowth`: decimal (0.10 = 10%) ✓
- `heldPercentInsiders`: decimal (0.05 = 5%) ✓
- `debtToEquity`: percentage (50 = 0.5 ratio) ⚠️ non-obvious
- `trailingPE`: actual ratio (15.3 = 15.3x) ✓
- `priceToBook`: actual ratio (1.2 = 1.2x) ✓
- `freeCashflow`: actual dollar amount ✓
- `marketCap`: actual dollar amount ✓

---

## Scan universe

Phase 1 scans ~200 hand-curated US tickers covering S&P 500 + NASDAQ-100 major constituents across all sectors (tech, financials, healthcare, consumer, energy, industrials, utilities).

The list lives in `screener.py → _US_UNIVERSE`. Wikipedia scraping was dropped because Cloudflare blocks Docker container IPs. The static list is updated manually when index constituents change significantly.

**Why not all US stocks?**

Scanning all 8,000+ US equities would take 4-6 hours and hit Yahoo Finance rate limits. ~200 liquid, data-complete stocks cover the most institutional-quality names. Phase 3 can expand this with a smarter caching layer.

---

## Planned improvements (Phase 3+)

- **Sector-relative P/E**: compare P/E to sector median instead of absolute 15
- **Earnings consistency**: penalize stocks with volatile or declining earnings
- **Dividend yield**: bonus for stocks with consistent dividend history
- **Piotroski F-Score**: 9-point financial health scoring system
- **Altman Z-Score**: bankruptcy risk predictor
- **Analyst consensus**: incorporate actual analyst ratings as a signal
