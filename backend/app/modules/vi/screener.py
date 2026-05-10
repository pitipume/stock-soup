"""
Fetches US stock universe and runs VI screening.
- Universe: S&P 500 + NASDAQ-100 pulled from Wikipedia
- Data source: yfinance (free, no API key needed)
- Each ticker fetch is synchronous — designed to run inside a Celery worker process
"""
import logging
import time
from typing import Optional

import yfinance as yf

from app.modules.vi.scorer import score_stock

logger = logging.getLogger(__name__)

# Static universe — S&P 500 + NASDAQ-100 representative tickers.
# Wikipedia scraping is blocked by Cloudflare in Docker environments.
# This list is updated manually and covers the major constituents.
_US_UNIVERSE = [
    # Mega-cap tech
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "AVGO", "ORCL",
    "AMD", "INTC", "QCOM", "TXN", "MU", "AMAT", "LRCX", "KLAC", "MRVL", "ADBE",
    "CRM", "NOW", "INTU", "PANW", "CRWD", "SNOW", "PLTR", "NET", "DDOG", "ZS",
    # Financials
    "BRK-B", "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "BLK", "SCHW",
    "COF", "USB", "PNC", "TFC", "MTB", "FITB", "HBAN", "CFG", "KEY", "RF",
    "V", "MA", "PYPL", "FIS", "FISV", "GPN", "SQ", "ICE", "CME", "CBOE",
    # Healthcare
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "PFE", "AMGN", "GILD", "BIIB", "REGN",
    "TMO", "ABT", "MDT", "SYK", "BSX", "EW", "ISRG", "ZBH", "BDX", "BAX",
    "CVS", "CI", "HUM", "CNC", "MOH", "ELV", "HCA", "THC", "DVA", "DGX",
    # Consumer
    "WMT", "COST", "TGT", "HD", "LOW", "MCD", "SBUX", "NKE", "TJX", "ROST",
    "KO", "PEP", "PG", "UL", "CL", "KMB", "GIS", "K", "HSY", "MKC",
    "AMZN", "EBAY", "ETSY", "W", "CHWY", "DASH", "UBER", "LYFT", "ABNB", "BKNG",
    # Energy
    "XOM", "CVX", "COP", "EOG", "SLB", "OXY", "PSX", "VLO", "MPC", "HES",
    "PXD", "DVN", "FANG", "APA", "HAL", "BKR", "MRO", "OKE", "WMB", "KMI",
    # Industrials
    "GE", "CAT", "DE", "HON", "LMT", "RTX", "NOC", "GD", "BA", "LHX",
    "UPS", "FDX", "CSX", "NSC", "UNP", "DAL", "UAL", "AAL", "LUV", "ALK",
    "MMM", "EMR", "ETN", "PH", "ROK", "IR", "XYL", "GWW", "FAST", "MSC",
    # Real estate / utilities / other
    "AMT", "PLD", "EQIX", "CCI", "SPG", "O", "WELL", "AVB", "EQR", "DRE",
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PEG", "ED", "ES",
    "BRK-B", "LIN", "APD", "SHW", "ECL", "PPG", "NEM", "FCX", "AA", "CLF",
]


def fetch_us_universe() -> list[str]:
    # Deduplicate and sort
    tickers = sorted(set(_US_UNIVERSE))
    logger.info(f"Universe: {len(tickers)} tickers (static list)")
    return tickers


def _fetch_ticker_data(ticker: str, retries: int = 2) -> Optional[dict]:
    for attempt in range(retries + 1):
        try:
            # Let yfinance manage its own curl_cffi session — required in newer versions
            t = yf.Ticker(ticker)
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
