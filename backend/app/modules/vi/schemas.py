from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class VIMetrics(BaseModel):
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    roe: Optional[float] = None
    revenue_growth: Optional[float] = None
    free_cash_flow: Optional[float] = None
    insider_ownership: Optional[float] = None
    market_cap: Optional[float] = None
    analyst_count: Optional[int] = None


class ScanResultOut(BaseModel):
    ticker: str
    company_name: str
    vi_score: float
    verdict: str
    metrics: VIMetrics

    model_config = {"from_attributes": True}


class ScanOut(BaseModel):
    id: int
    status: str
    total_scanned: int
    results_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ScanWithResults(ScanOut):
    results: list[ScanResultOut] = []
