"""
Fetches US stock universe and runs VI screening.
- Universe: S&P 500 + NASDAQ-100 pulled from Wikipedia
- Data source: yfinance (free, no API key needed)
- Each ticker fetch is synchronous — designed to run inside a Celery worker process
"""
import logging
import time
from typing import Optional

import pandas as pd
import yfinance as yf

from app.modules.vi.scorer import score_stock

logger = logging.getLogger(__name__)

_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_NASDAQ100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"

# Fallback list for when Wikipedia fetch fails (dev/offline use)
_FALLBACK_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "BRK-B",
    "JPM", "JNJ", "V", "PG", "MA", "HD", "UNH", "DIS", "BAC", "XOM",
    "ABBV", "PFE", "WMT", "CVX", "KO", "PEP", "MRK", "TMO", "AVGO",
]


def fetch_us_universe() -> list[str]:
    tickers: set[str] = set()

    try:
        sp500_df = pd.read_html(_SP500_URL)[0]
        tickers.update(sp500_df["Symbol"].tolist())
        logger.info(f"Fetched {len(tickers)} S&P 500 tickers")
    except Exception as e:
        logger.warning(f"S&P 500 fetch failed: {e}")

    try:
        nasdaq_tables = pd.read_html(_NASDAQ100_URL)
        # The ticker column location varies — search all tables
        for table in nasdaq_tables:
            if "Ticker" in table.columns:
                tickers.update(table["Ticker"].dropna().tolist())
                break
        logger.info(f"Total universe after NASDAQ-100: {len(tickers)}")
    except Exception as e:
        logger.warning(f"NASDAQ-100 fetch failed: {e}")

    if not tickers:
        logger.warning("Using fallback ticker list")
        return _FALLBACK_TICKERS

    return sorted(tickers)


_SESSION = None


def _get_session():
    """
    Shared requests session with browser-like headers.
    Yahoo Finance blocks default Python user agents aggressively in cloud/Docker environments.
    """
    global _SESSION
    if _SESSION is None:
        import requests
        _SESSION = requests.Session()
        _SESSION.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        })
    return _SESSION


def _fetch_ticker_data(ticker: str, retries: int = 2) -> Optional[dict]:
    for attempt in range(retries + 1):
        try:
            t = yf.Ticker(ticker, session=_get_session())
            info = t.info
            if not info or (not info.get("regularMarketPrice") and not info.get("currentPrice")):
                return None

            return {
                "ticker": ticker,
                "company_name": info.get("longName") or info.get("shortName") or ticker,
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "metrics": {
                    "pe_ratio": info.get("trailingPE"),
                    "pb_ratio": info.get("priceToBook"),
                    "debt_to_equity": info.get("debtToEquity"),
                    "roe": info.get("returnOnEquity"),
                    "revenue_growth": info.get("revenueGrowth"),
                    "free_cash_flow": info.get("freeCashflow"),
                    "insider_ownership": info.get("heldPercentInsiders"),
                    "market_cap": info.get("marketCap"),
                    "analyst_count": info.get("numberOfAnalystOpinions"),
                },
            }
        except Exception as e:
            err = str(e)
            if "429" in err and attempt < retries:
                wait = 5 * (attempt + 1)
                logger.warning(f"Rate limited on {ticker}, retrying in {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
            else:
                logger.warning(f"Failed to fetch {ticker}: {e}")
                return None
    return None


def run_vi_scan(tickers: list[str]) -> list[dict]:
    """
    Scans all tickers. Returns results sorted by VI score descending,
    excluding 'skip' verdicts. Runs synchronously — call from a worker process.

    Note: Yahoo Finance rate-limits aggressively in containerized environments.
    The 1-second delay between requests is a minimum — scans may take 20-40 min.
    """
    results = []

    for i, ticker in enumerate(tickers):
        data = _fetch_ticker_data(ticker)
        if data is not None:
            vi_score, verdict = score_stock(data["metrics"])
            if verdict != "skip":
                results.append({
                    "ticker": data["ticker"],
                    "company_name": data["company_name"],
                    "vi_score": vi_score,
                    "verdict": verdict,
                    "metrics": data["metrics"],
                })

        # 1-second pause per request to stay under Yahoo Finance rate limits
        time.sleep(1)

        if i > 0 and i % 20 == 0:
            logger.info(f"Progress: {i}/{len(tickers)} tickers, {len(results)} passing VI criteria")

    return sorted(results, key=lambda x: x["vi_score"], reverse=True)
