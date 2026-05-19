"""
Pine Script v5 export for each strategy.
Templates mirror the logic in our Python strategies so TradingView results
match what the live bot does. Parameters are injected from the request.
"""
from typing import Any

_HEADER = """//@version=5
strategy("{title}", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=1, pyramiding=0)

// ── Risk ─────────────────────────────────────────────────────────────────────
leverage     = input.int({leverage}, title="Leverage", minval=1, maxval=125)
risk_pct     = input.float(1.0, title="Risk % per trade", minval=0.1, maxval=5) / 100
"""

_RSI = """//@version=5
strategy("RSI Strategy (StockSoup)", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=1)

// ── Inputs ────────────────────────────────────────────────────────────────────
rsi_period  = input.int({rsi_period}, title="RSI Period", minval=2)
oversold    = input.float({oversold}, title="Oversold Level", minval=10, maxval=49)
overbought  = input.float({overbought}, title="Overbought Level", minval=51, maxval=90)
sl_pct      = input.float({sl_pct}, title="Stop Loss %", minval=0.1) / 100
rr          = input.float({rr}, title="Risk:Reward Ratio", minval=1.0)

// ── Indicator ─────────────────────────────────────────────────────────────────
rsi = ta.rsi(close, rsi_period)

// ── Signals ───────────────────────────────────────────────────────────────────
long_entry  = ta.crossover(rsi, oversold)
short_entry = ta.crossunder(rsi, overbought)

// ── Execution ─────────────────────────────────────────────────────────────────
if long_entry and strategy.position_size == 0
    sl = close * (1 - sl_pct)
    tp = close * (1 + sl_pct * rr)
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", "Long", stop=sl, limit=tp)

if short_entry and strategy.position_size == 0
    sl = close * (1 + sl_pct)
    tp = close * (1 - sl_pct * rr)
    strategy.entry("Short", strategy.short)
    strategy.exit("Exit Short", "Short", stop=sl, limit=tp)

// ── Plots ─────────────────────────────────────────────────────────────────────
hline(oversold,   "Oversold",   color=color.green, linestyle=hline.style_dashed)
hline(overbought, "Overbought", color=color.red,   linestyle=hline.style_dashed)
plot(rsi, title="RSI", color=color.blue)
"""

_MACD = """//@version=5
strategy("MACD Strategy (StockSoup)", overlay=false, default_qty_type=strategy.percent_of_equity, default_qty_value=1)

// ── Inputs ────────────────────────────────────────────────────────────────────
fast_len    = input.int({fast}, title="Fast EMA", minval=2)
slow_len    = input.int({slow}, title="Slow EMA", minval=2)
signal_len  = input.int({signal}, title="Signal", minval=1)
sl_pct      = input.float({sl_pct}, title="Stop Loss %", minval=0.1) / 100
rr          = input.float({rr}, title="Risk:Reward", minval=1.0)

// ── Indicator ─────────────────────────────────────────────────────────────────
[macdLine, signalLine, hist] = ta.macd(close, fast_len, slow_len, signal_len)
ema200 = ta.ema(close, 200)

// ── Signals ───────────────────────────────────────────────────────────────────
long_entry  = ta.crossover(macdLine, signalLine)  and close > ema200
short_entry = ta.crossunder(macdLine, signalLine) and close < ema200

// ── Execution ─────────────────────────────────────────────────────────────────
if long_entry and strategy.position_size == 0
    sl = close * (1 - sl_pct)
    tp = close * (1 + sl_pct * rr)
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", "Long", stop=sl, limit=tp)

if short_entry and strategy.position_size == 0
    sl = close * (1 + sl_pct)
    tp = close * (1 - sl_pct * rr)
    strategy.entry("Short", strategy.short)
    strategy.exit("Exit Short", "Short", stop=sl, limit=tp)

// ── Plots ─────────────────────────────────────────────────────────────────────
plot(macdLine,   title="MACD",   color=color.blue)
plot(signalLine, title="Signal", color=color.orange)
plot(hist,       title="Hist",   color=hist >= 0 ? color.green : color.red, style=plot.style_histogram)
"""

_BOLLINGER = """//@version=5
strategy("Bollinger Bands Strategy (StockSoup)", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=1)

// ── Inputs ────────────────────────────────────────────────────────────────────
bb_period   = input.int({period}, title="BB Period", minval=5)
bb_mult     = input.float({mult}, title="BB StdDev", minval=0.5, step=0.1)
sl_pct      = input.float({sl_pct}, title="Stop Loss %", minval=0.1) / 100
rr          = input.float({rr}, title="Risk:Reward", minval=1.0)

// ── Indicator ─────────────────────────────────────────────────────────────────
[mid, upper, lower] = ta.bb(close, bb_period, bb_mult)

// ── Signals ───────────────────────────────────────────────────────────────────
long_entry  = ta.crossover(close, lower)
short_entry = ta.crossunder(close, upper)

// ── Execution ─────────────────────────────────────────────────────────────────
if long_entry and strategy.position_size == 0
    sl = close * (1 - sl_pct)
    tp = close * (1 + sl_pct * rr)
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", "Long", stop=sl, limit=tp)

if short_entry and strategy.position_size == 0
    sl = close * (1 + sl_pct)
    tp = close * (1 - sl_pct * rr)
    strategy.entry("Short", strategy.short)
    strategy.exit("Exit Short", "Short", stop=sl, limit=tp)

// ── Plots ─────────────────────────────────────────────────────────────────────
plot(upper, title="Upper",  color=color.red,   linewidth=1)
plot(mid,   title="Middle", color=color.gray,  linewidth=1)
plot(lower, title="Lower",  color=color.green, linewidth=1)
"""

_FIBONACCI = """//@version=5
strategy("Fibonacci Retracement Strategy (StockSoup)", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=1)

// ── Inputs ────────────────────────────────────────────────────────────────────
lookback    = input.int({lookback}, title="Swing Lookback", minval=5)
fib_entry   = input.float({fib_entry}, title="Fib Entry Level", minval=0.1, maxval=0.9, step=0.01)
sl_pct      = input.float({sl_pct}, title="Stop Loss %", minval=0.1) / 100
rr          = input.float({rr}, title="Risk:Reward", minval=1.0)

// ── Swing Points ──────────────────────────────────────────────────────────────
swing_high = ta.highest(high, lookback)
swing_low  = ta.lowest(low,  lookback)
range_size = swing_high - swing_low

fib_382 = swing_high - range_size * 0.382
fib_500 = swing_high - range_size * 0.500
fib_618 = swing_high - range_size * 0.618

// ── Signals ───────────────────────────────────────────────────────────────────
// Long: price touches 61.8% retracement in uptrend (recent higher low)
long_entry  = close <= fib_618 and close > swing_low and ta.rising(close, 3)
short_entry = close >= fib_382 and close < swing_high and ta.falling(close, 3)

// ── Execution ─────────────────────────────────────────────────────────────────
if long_entry and strategy.position_size == 0
    sl = close * (1 - sl_pct)
    tp = close * (1 + sl_pct * rr)
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", "Long", stop=sl, limit=tp)

if short_entry and strategy.position_size == 0
    sl = close * (1 + sl_pct)
    tp = close * (1 - sl_pct * rr)
    strategy.entry("Short", strategy.short)
    strategy.exit("Exit Short", "Short", stop=sl, limit=tp)

// ── Plots ─────────────────────────────────────────────────────────────────────
plot(fib_382, title="Fib 38.2%", color=color.yellow, linewidth=1)
plot(fib_500, title="Fib 50.0%", color=color.orange, linewidth=1)
plot(fib_618, title="Fib 61.8%", color=color.red,    linewidth=1)
"""

_ELLIOTT_WAVE = """//@version=5
strategy("Elliott Wave Strategy (StockSoup)", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=1)

// ── Inputs ────────────────────────────────────────────────────────────────────
wave_period = input.int({wave_period}, title="Wave Detection Period", minval=5)
min_wave    = input.float({min_wave_pct}, title="Min Wave Size %", minval=0.5) / 100
sl_pct      = input.float({sl_pct}, title="Stop Loss %", minval=0.1) / 100
rr          = input.float({rr}, title="Risk:Reward", minval=1.0)

// ── Wave Detection (simplified) ───────────────────────────────────────────────
high1 = ta.highest(high, wave_period)
low1  = ta.lowest(low,  wave_period)
wave_size = (high1 - low1) / low1

uptrend_wave   = wave_size >= min_wave and close > ta.ema(close, 50) and ta.rsi(close, 14) < 65
downtrend_wave = wave_size >= min_wave and close < ta.ema(close, 50) and ta.rsi(close, 14) > 35

long_entry  = uptrend_wave   and ta.crossover(close,  ta.ema(close, 21))
short_entry = downtrend_wave and ta.crossunder(close, ta.ema(close, 21))

// ── Execution ─────────────────────────────────────────────────────────────────
if long_entry and strategy.position_size == 0
    sl = close * (1 - sl_pct)
    tp = close * (1 + sl_pct * rr)
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", "Long", stop=sl, limit=tp)

if short_entry and strategy.position_size == 0
    sl = close * (1 + sl_pct)
    tp = close * (1 - sl_pct * rr)
    strategy.entry("Short", strategy.short)
    strategy.exit("Exit Short", "Short", stop=sl, limit=tp)

// ── Plots ─────────────────────────────────────────────────────────────────────
plot(ta.ema(close, 21), title="EMA 21", color=color.blue)
plot(ta.ema(close, 50), title="EMA 50", color=color.orange)
"""

_COMBINED = """//@version=5
strategy("Combined Score Strategy (StockSoup)", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=1)

// ── Inputs ────────────────────────────────────────────────────────────────────
threshold   = input.float({threshold}, title="Signal Threshold", minval=0.1, maxval=1.0, step=0.05)
sl_pct      = input.float({sl_pct}, title="Stop Loss %", minval=0.1) / 100
rr          = input.float({rr}, title="Risk:Reward", minval=1.0)

rsi_w  = input.float(0.5, title="RSI Weight",    minval=0, maxval=1, step=0.1)
macd_w = input.float(0.5, title="MACD Weight",   minval=0, maxval=1, step=0.1)
bb_w   = input.float(0.5, title="BB Weight",     minval=0, maxval=1, step=0.1)
fib_w  = input.float(0.5, title="Fib Weight",    minval=0, maxval=1, step=0.1)
ew_w   = input.float(0.5, title="Elliott Weight",minval=0, maxval=1, step=0.1)

// ── Sub-strategy signals ──────────────────────────────────────────────────────
rsi_val = ta.rsi(close, 14)
rsi_long  = ta.crossover(rsi_val, 30)  ? 1 : 0
rsi_short = ta.crossunder(rsi_val, 70) ? 1 : 0

[macdL, macdS, _] = ta.macd(close, 12, 26, 9)
ema200 = ta.ema(close, 200)
macd_long  = ta.crossover(macdL, macdS)  and close > ema200 ? 1 : 0
macd_short = ta.crossunder(macdL, macdS) and close < ema200 ? 1 : 0

[_, bbU, bbL] = ta.bb(close, 20, 2.0)
bb_long  = ta.crossover(close, bbL)  ? 1 : 0
bb_short = ta.crossunder(close, bbU) ? 1 : 0

// ── Combined score ────────────────────────────────────────────────────────────
long_score  = rsi_w * rsi_long  + macd_w * macd_long  + bb_w * bb_long
short_score = rsi_w * rsi_short + macd_w * macd_short + bb_w * bb_short

long_entry  = long_score  >= threshold and short_score < threshold * 0.5
short_entry = short_score >= threshold and long_score  < threshold * 0.5

// ── Execution ─────────────────────────────────────────────────────────────────
if long_entry and strategy.position_size == 0
    sl = close * (1 - sl_pct)
    tp = close * (1 + sl_pct * rr)
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", "Long", stop=sl, limit=tp)

if short_entry and strategy.position_size == 0
    sl = close * (1 + sl_pct)
    tp = close * (1 - sl_pct * rr)
    strategy.entry("Short", strategy.short)
    strategy.exit("Exit Short", "Short", stop=sl, limit=tp)

// ── Plots ─────────────────────────────────────────────────────────────────────
plot(ema200, title="EMA 200", color=color.gray, linewidth=1)
"""


def generate(strategy: str, params: dict) -> str:
    p = params

    def g(key: str, default: Any) -> Any:
        return p.get(key, default)

    if strategy == "rsi":
        return _RSI.format(
            rsi_period=int(g("rsi_period", 14)),
            oversold=g("oversold", 30),
            overbought=g("overbought", 70),
            sl_pct=g("sl_pct", 2.0),
            rr=g("rr", 2.0),
        )
    elif strategy == "macd":
        return _MACD.format(
            fast=int(g("fast", 12)),
            slow=int(g("slow", 26)),
            signal=int(g("signal", 9)),
            sl_pct=g("sl_pct", 2.0),
            rr=g("rr", 2.0),
        )
    elif strategy == "bollinger":
        return _BOLLINGER.format(
            period=int(g("period", 20)),
            mult=g("mult", 2.0),
            sl_pct=g("sl_pct", 2.0),
            rr=g("rr", 2.0),
        )
    elif strategy == "fibonacci":
        return _FIBONACCI.format(
            lookback=int(g("lookback", 20)),
            fib_entry=g("fib_entry", 0.618),
            sl_pct=g("sl_pct", 2.0),
            rr=g("rr", 2.0),
        )
    elif strategy == "elliott_wave":
        return _ELLIOTT_WAVE.format(
            wave_period=int(g("wave_period", 20)),
            min_wave_pct=g("min_wave_pct", 3.0),
            sl_pct=g("sl_pct", 2.0),
            rr=g("rr", 2.0),
        )
    elif strategy == "combined":
        return _COMBINED.format(
            threshold=g("threshold", 0.6),
            sl_pct=g("sl_pct", 2.0),
            rr=g("rr", 2.0),
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
