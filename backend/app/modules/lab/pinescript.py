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


_TRIPLE_EMA_STOCH_RSI = """//@version=5
// Triple EMA + Stochastic RSI Strategy (StockSoup)
// Strategy concept inspired by TTMW STR: Triple EMA + Stochastic RSI
// Original indicator by stampknvt (TradingView) — https://www.tradingview.com/script/BVp0qP4Z-TTMW-STR-Triple-EMA-Stochastic-RSI-a001/
// Adapted for algorithmic backtesting by StockSoup
strategy("Triple EMA + StochRSI (StockSoup)", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=1)

// ── Inputs ────────────────────────────────────────────────────────────────────
ema_fast    = input.int({ema_fast},   title="Fast EMA",    minval=2)
ema_slow    = input.int({ema_slow},   title="Slow EMA",    minval=2)
ema_filter  = input.int({ema_filter}, title="Filter EMA",  minval=50)
rsi_period  = input.int({rsi_period}, title="RSI Period",  minval=2)
stoch_period= input.int({stoch_period},title="Stoch Period",minval=2)
k_smooth    = input.int({k_smooth},   title="K Smooth",    minval=1)
d_smooth    = input.int({d_smooth},   title="D Smooth",    minval=1)
oversold    = input.float({oversold}, title="Oversold",    minval=5,  maxval=40)
overbought  = input.float({overbought},title="Overbought", minval=60, maxval=95)
rr          = input.float({rr},       title="Risk:Reward", minval=1.0)

// ── EMAs ──────────────────────────────────────────────────────────────────────
emaf   = ta.ema(close, ema_fast)
emas   = ta.ema(close, ema_slow)
emafil = ta.ema(close, ema_filter)

bullish_ema = emaf > emas and emas > emafil
bearish_ema = emaf < emas and emas < emafil

// ── Stochastic RSI ────────────────────────────────────────────────────────────
rsi_val = ta.rsi(close, rsi_period)
k_raw   = ta.stoch(rsi_val, rsi_val, rsi_val, stoch_period)
k       = ta.sma(k_raw, k_smooth)
d       = ta.sma(k, d_smooth)

// ── Signals ───────────────────────────────────────────────────────────────────
long_cross  = ta.crossover(k, d)  and k[1] < oversold
short_cross = ta.crossunder(k, d) and k[1] > overbought

long_entry  = bullish_ema and long_cross
short_entry = bearish_ema and short_cross

// ── SL: lowest low / highest high of last 3 bars ──────────────────────────────
sl_long  = ta.lowest(low,  3)
sl_short = ta.highest(high, 3)

// ── Execution ─────────────────────────────────────────────────────────────────
if long_entry and strategy.position_size == 0
    risk = close - sl_long
    tp   = close + risk * rr
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", "Long", stop=sl_long, limit=tp)

if short_entry and strategy.position_size == 0
    risk = sl_short - close
    tp   = close - risk * rr
    strategy.entry("Short", strategy.short)
    strategy.exit("Exit Short", "Short", stop=sl_short, limit=tp)

// ── Plots ─────────────────────────────────────────────────────────────────────
plot(emaf,   title="EMA Fast",   color=color.new(color.blue,   0), linewidth=1)
plot(emas,   title="EMA Slow",   color=color.new(color.orange, 0), linewidth=1)
plot(emafil, title="EMA Filter", color=color.new(color.gray,   0), linewidth=2)
bgcolor(long_entry  ? color.new(color.green, 85) : na)
bgcolor(short_entry ? color.new(color.red,   85) : na)
"""


_THREE_GOLDEN = """//@version=5
// Three Golden Strategy (StockSoup)
// Concept inspired by "Three Golden" by Moonalert (TradingView)
// Original: https://www.tradingview.com/script/bqbaMOSM/
// Adapted for algorithmic backtesting by StockSoup
strategy("Three Golden (StockSoup)", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=1)

// ── Inputs ────────────────────────────────────────────────────────────────────
rsi_period  = input.int({rsi_period},  title="RSI Period",   minval=2)
bb_period   = input.int({bb_period},   title="BB Period",    minval=5)
macd_fast   = input.int({macd_fast},   title="MACD Fast",    minval=2)
macd_slow   = input.int({macd_slow},   title="MACD Slow",    minval=2)
atr_period  = input.int({atr_period},  title="ATR Period",   minval=1)
atr_mult    = input.float({atr_mult},  title="ATR Multiplier", minval=0.1, step=0.1)
rr          = input.float({rr},        title="Risk:Reward",  minval=1.0)

// ── Indicators ────────────────────────────────────────────────────────────────
rsi_val             = ta.rsi(close, rsi_period)
bb_mid              = ta.sma(close, bb_period)
[macdLine, _, _]    = ta.macd(close, macd_fast, macd_slow, 9)
atr                 = ta.atr(atr_period)

// ── Consensus ─────────────────────────────────────────────────────────────────
bull = close > bb_mid and rsi_val > 50 and macdLine > 0
bear = close < bb_mid and rsi_val < 50 and macdLine < 0

// Signal on first bar where consensus forms
long_entry  = bull and not bull[1]
short_entry = bear and not bear[1]

// ── Execution ─────────────────────────────────────────────────────────────────
if long_entry and strategy.position_size == 0
    sl = close - atr * atr_mult
    tp = close + atr * atr_mult * rr
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", "Long", stop=sl, limit=tp)

if short_entry and strategy.position_size == 0
    sl = close + atr * atr_mult
    tp = close - atr * atr_mult * rr
    strategy.entry("Short", strategy.short)
    strategy.exit("Exit Short", "Short", stop=sl, limit=tp)

// ── Plots ─────────────────────────────────────────────────────────────────────
plot(bb_mid, title="BB Mid", color=color.gray, linewidth=1)
bgcolor(long_entry  ? color.new(color.green, 85) : na)
bgcolor(short_entry ? color.new(color.red,   85) : na)
"""

_SUPERTREND = """//@version=5
// Supertrend Strategy (StockSoup)
strategy("Supertrend (StockSoup)", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=1)

// ── Inputs ────────────────────────────────────────────────────────────────────
atr_period  = input.int({atr_period},   title="ATR Period",     minval=1)
atr_mult    = input.float({atr_mult},   title="ATR Multiplier", minval=0.1, step=0.1)
rr          = input.float({rr},         title="Risk:Reward",    minval=1.0)

// ── Supertrend ────────────────────────────────────────────────────────────────
[supertrend, direction] = ta.supertrend(atr_mult, atr_period)

long_entry  = direction == 1  and direction[1] == -1
short_entry = direction == -1 and direction[1] == 1

// ── Execution ─────────────────────────────────────────────────────────────────
if long_entry and strategy.position_size == 0
    sl = supertrend
    risk = close - sl
    tp = close + risk * rr
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit Long", "Long", stop=sl, limit=tp)

if short_entry and strategy.position_size == 0
    sl = supertrend
    risk = sl - close
    tp = close - risk * rr
    strategy.entry("Short", strategy.short)
    strategy.exit("Exit Short", "Short", stop=sl, limit=tp)

// ── Plots ─────────────────────────────────────────────────────────────────────
plot(direction == 1 ? supertrend : na, title="Bullish", color=color.green, linewidth=2, style=plot.style_linebr)
plot(direction == -1 ? supertrend : na, title="Bearish", color=color.red,  linewidth=2, style=plot.style_linebr)
bgcolor(long_entry  ? color.new(color.green, 85) : na)
bgcolor(short_entry ? color.new(color.red,   85) : na)
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
    elif strategy == "triple_ema_stoch_rsi":
        return _TRIPLE_EMA_STOCH_RSI.format(
            ema_fast=int(g("ema_fast", 12)),
            ema_slow=int(g("ema_slow", 26)),
            ema_filter=int(g("ema_filter", 200)),
            rsi_period=int(g("rsi_period", 14)),
            stoch_period=int(g("stoch_period", 14)),
            k_smooth=int(g("k_smooth", 3)),
            d_smooth=int(g("d_smooth", 3)),
            oversold=g("oversold", 20),
            overbought=g("overbought", 80),
            rr=g("rr", 2.0),
        )
    elif strategy == "three_golden":
        return _THREE_GOLDEN.format(
            rsi_period=int(g("rsi_period", 14)),
            bb_period=int(g("bb_period", 20)),
            macd_fast=int(g("macd_fast", 12)),
            macd_slow=int(g("macd_slow", 26)),
            atr_period=int(g("atr_period", 14)),
            atr_mult=g("atr_multiplier", 1.0),
            rr=g("rr_ratio", 2.0),
        )
    elif strategy == "supertrend":
        return _SUPERTREND.format(
            atr_period=int(g("atr_period", 10)),
            atr_mult=g("atr_multiplier", 3.0),
            rr=g("rr_ratio", 2.0),
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
