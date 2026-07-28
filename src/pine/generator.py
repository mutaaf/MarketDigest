"""Pine Script generator — creates TradingView Pine Script v5 from strategy configs."""

from pathlib import Path

import yaml

from src.utils.logging_config import get_logger

logger = get_logger("pine_generator")

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "signals.yaml"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def generate_pine_script(strategy: str = "ema_crossover", custom_params: dict | None = None) -> str:
    """Generate a TradingView Pine Script v5 strategy.

    Args:
        strategy: One of 'ema_crossover', 'rsi_divergence', 'bollinger_squeeze', 'multi_confluence'
        custom_params: Override default indicator parameters

    Returns:
        Valid Pine Script v5 string
    """
    config = _load_config()
    params = {**config.get("indicators", {}), **(custom_params or {})}
    trade_mgmt = config.get("trade_management", {})

    generators = {
        "ema_crossover": _gen_ema_crossover,
        "rsi_divergence": _gen_rsi_divergence,
        "bollinger_squeeze": _gen_bollinger_squeeze,
        "multi_confluence": _gen_multi_confluence,
        "ema_trend_pullback": _gen_ema_trend_pullback,
        "donchian_breakout": _gen_donchian_breakout,
        "rsi2_momentum": _gen_rsi2_momentum,
        "pivot_bounce": _gen_pivot_bounce,
        "macd_divergence": _gen_macd_divergence,
        "volatility_squeeze": _gen_volatility_squeeze,
    }

    gen_func = generators.get(strategy, _gen_multi_confluence)
    return gen_func(params, trade_mgmt)


def _gen_ema_crossover(params: dict, mgmt: dict) -> str:
    return f"""//@version=5
strategy("EMA Crossover + RSI Filter [Signal Forge]", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=2)

// === Inputs ===
fast_len = input.int({params.get('ema_fast', 9)}, "Fast EMA", minval=1)
slow_len = input.int({params.get('ema_slow', 21)}, "Slow EMA", minval=1)
rsi_len = input.int({params.get('rsi_period', 14)}, "RSI Period", minval=1)
rsi_ob = input.int({params.get('rsi_overbought', 70)}, "RSI Overbought")
rsi_os = input.int({params.get('rsi_oversold', 30)}, "RSI Oversold")
atr_len = input.int({params.get('atr_period', 14)}, "ATR Period")
atr_mult = input.float(1.5, "Stop ATR Multiplier", step=0.1)
rr_ratio = input.float({mgmt.get('target_1_r', 2.0)}, "Risk:Reward Ratio", step=0.1)

// === Calculations ===
fast_ema = ta.ema(close, fast_len)
slow_ema = ta.ema(close, slow_len)
rsi = ta.rsi(close, rsi_len)
atr = ta.atr(atr_len)

// === Signals ===
long_cond = ta.crossover(fast_ema, slow_ema) and rsi < rsi_ob and rsi > rsi_os
short_cond = ta.crossunder(fast_ema, slow_ema) and rsi > rsi_os and rsi < rsi_ob

// === Risk Management (2:1 minimum) ===
long_stop = close - atr * atr_mult
long_target = close + (close - long_stop) * rr_ratio
short_stop = close + atr * atr_mult
short_target = close - (short_stop - close) * rr_ratio

// === Entries ===
if long_cond
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", stop=long_stop, limit=long_target)

if short_cond
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", stop=short_stop, limit=short_target)

// === Plots ===
plot(fast_ema, "Fast EMA", color=color.new(color.blue, 0), linewidth=2)
plot(slow_ema, "Slow EMA", color=color.new(color.orange, 0), linewidth=2)

// Signal markers
plotshape(long_cond, "Buy", shape.triangleup, location.belowbar, color.green, size=size.small)
plotshape(short_cond, "Sell", shape.triangledown, location.abovebar, color.red, size=size.small)
"""


def _gen_rsi_divergence(params: dict, mgmt: dict) -> str:
    return f"""//@version=5
strategy("RSI Divergence + Pivot Levels [Signal Forge]", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=2)

// === Inputs ===
rsi_len = input.int({params.get('rsi_period', 14)}, "RSI Period")
rsi_os = input.int({params.get('rsi_oversold', 30)}, "RSI Oversold")
rsi_ob = input.int({params.get('rsi_overbought', 70)}, "RSI Overbought")
atr_len = input.int({params.get('atr_period', 14)}, "ATR Period")
atr_mult = input.float(1.5, "Stop ATR Multiplier", step=0.1)
rr_ratio = input.float({mgmt.get('target_1_r', 2.0)}, "Risk:Reward Ratio", step=0.1)
pivot_len = input.int(5, "Pivot Lookback")

// === Calculations ===
rsi = ta.rsi(close, rsi_len)
atr = ta.atr(atr_len)
pivot_high = ta.pivothigh(high, pivot_len, pivot_len)
pivot_low = ta.pivotlow(low, pivot_len, pivot_len)

// === Divergence Detection ===
// Bullish: price makes lower low, RSI makes higher low
bull_div = (not na(pivot_low)) and (low[pivot_len] < ta.lowest(low, pivot_len * 2)[pivot_len + 1]) and (rsi[pivot_len] > ta.lowest(rsi, pivot_len * 2)[pivot_len + 1]) and rsi < 45
// Bearish: price makes higher high, RSI makes lower high
bear_div = (not na(pivot_high)) and (high[pivot_len] > ta.highest(high, pivot_len * 2)[pivot_len + 1]) and (rsi[pivot_len] < ta.highest(rsi, pivot_len * 2)[pivot_len + 1]) and rsi > 55

// === Risk Management ===
long_stop = close - atr * atr_mult
long_target = close + (close - long_stop) * rr_ratio
short_stop = close + atr * atr_mult
short_target = close - (short_stop - close) * rr_ratio

// === Entries ===
if bull_div
    strategy.entry("Long", strategy.long)
    strategy.exit("Long TP/SL", "Long", stop=long_stop, limit=long_target)

if bear_div
    strategy.entry("Short", strategy.short)
    strategy.exit("Short TP/SL", "Short", stop=short_stop, limit=short_target)

plotshape(bull_div, "Bull Div", shape.triangleup, location.belowbar, color.green, size=size.small)
plotshape(bear_div, "Bear Div", shape.triangledown, location.abovebar, color.red, size=size.small)
"""


def _gen_bollinger_squeeze(params: dict, mgmt: dict) -> str:
    return f"""//@version=5
strategy("Bollinger Squeeze Breakout [Signal Forge]", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=2)

// === Inputs ===
bb_len = input.int({params.get('bb_period', 20)}, "BB Period")
bb_mult = input.float({params.get('bb_std', 2.0)}, "BB StdDev", step=0.1)
ema_fast = input.int({params.get('ema_fast', 9)}, "Fast EMA")
ema_slow = input.int({params.get('ema_slow', 21)}, "Slow EMA")
atr_len = input.int({params.get('atr_period', 14)}, "ATR Period")
atr_mult = input.float(1.5, "Stop ATR Multiplier", step=0.1)
rr_ratio = input.float({mgmt.get('target_1_r', 2.0)}, "Risk:Reward Ratio", step=0.1)
squeeze_threshold = input.float(4.0, "Squeeze Bandwidth %", step=0.5)

// === Calculations ===
[middle, upper, lower] = ta.bb(close, bb_len, bb_mult)
bandwidth = (upper - lower) / middle * 100
squeeze = bandwidth < squeeze_threshold
was_squeeze = squeeze[1] and not squeeze

ema_f = ta.ema(close, ema_fast)
ema_s = ta.ema(close, ema_slow)
atr = ta.atr(atr_len)

// === Signals (breakout from squeeze) ===
long_cond = was_squeeze and close > upper and ema_f > ema_s
short_cond = was_squeeze and close < lower and ema_f < ema_s

// === Risk Management ===
long_stop = close - atr * atr_mult
long_target = close + (close - long_stop) * rr_ratio
short_stop = close + atr * atr_mult
short_target = close - (short_stop - close) * rr_ratio

if long_cond
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", stop=long_stop, limit=long_target)

if short_cond
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", stop=short_stop, limit=short_target)

// === Plots ===
plot(upper, "Upper BB", color.new(color.blue, 50))
plot(middle, "Middle BB", color.new(color.gray, 50))
plot(lower, "Lower BB", color.new(color.blue, 50))
bgcolor(squeeze ? color.new(color.yellow, 90) : na)
plotshape(long_cond, "Buy", shape.triangleup, location.belowbar, color.green, size=size.small)
plotshape(short_cond, "Sell", shape.triangledown, location.abovebar, color.red, size=size.small)
"""


def _gen_multi_confluence(params: dict, mgmt: dict) -> str:
    return f"""//@version=5
strategy("Multi-Confluence Signal [Signal Forge]", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=2)

// === Inputs ===
ema_fast = input.int({params.get('ema_fast', 9)}, "Fast EMA")
ema_slow = input.int({params.get('ema_slow', 21)}, "Slow EMA")
ema_trend = input.int({params.get('ema_trend', 50)}, "Trend EMA")
rsi_len = input.int({params.get('rsi_period', 14)}, "RSI Period")
bb_len = input.int({params.get('bb_period', 20)}, "BB Period")
bb_mult = input.float({params.get('bb_std', 2.0)}, "BB StdDev", step=0.1)
stoch_k = input.int({params.get('stoch_k', 14)}, "Stoch K")
stoch_d = input.int({params.get('stoch_d', 3)}, "Stoch D")
stoch_smooth = input.int({params.get('stoch_smooth', 3)}, "Stoch Smooth")
macd_fast = input.int({params.get('macd_fast', 12)}, "MACD Fast")
macd_slow = input.int({params.get('macd_slow', 26)}, "MACD Slow")
macd_sig = input.int({params.get('macd_signal', 9)}, "MACD Signal")
atr_len = input.int({params.get('atr_period', 14)}, "ATR Period")
atr_mult = input.float(1.5, "Stop ATR Multiplier", step=0.1)
rr_ratio = input.float({mgmt.get('target_1_r', 2.0)}, "Risk:Reward Ratio", step=0.1)
min_score = input.int(4, "Min Confluence Score (out of 6)", minval=1, maxval=6)

// === Calculations ===
ema_f = ta.ema(close, ema_fast)
ema_s = ta.ema(close, ema_slow)
ema_t = ta.ema(close, ema_trend)
rsi = ta.rsi(close, rsi_len)
[bb_mid, bb_up, bb_lo] = ta.bb(close, bb_len, bb_mult)
k = ta.stoch(close, high, low, stoch_k)
d = ta.sma(k, stoch_d)
[macd_line, sig_line, hist] = ta.macd(close, macd_fast, macd_slow, macd_sig)
atr = ta.atr(atr_len)

// === Confluence Scoring ===
bull_score = 0
bear_score = 0

// 1. EMA Cross
bull_score += ema_f > ema_s ? 1 : 0
bear_score += ema_f < ema_s ? 1 : 0

// 2. Trend Filter
bull_score += close > ema_t ? 1 : 0
bear_score += close < ema_t ? 1 : 0

// 3. RSI Zone
bull_score += rsi > 30 and rsi < 60 ? 1 : 0
bear_score += rsi < 70 and rsi > 40 ? 1 : 0

// 4. Bollinger Position
bull_score += close < bb_mid ? 1 : 0
bear_score += close > bb_mid ? 1 : 0

// 5. Stochastic
bull_score += k < 50 and k > d ? 1 : 0
bear_score += k > 50 and k < d ? 1 : 0

// 6. MACD
bull_score += hist > 0 ? 1 : 0
bear_score += hist < 0 ? 1 : 0

// === Signals ===
long_cond = bull_score >= min_score and ta.crossover(ema_f, ema_s)
short_cond = bear_score >= min_score and ta.crossunder(ema_f, ema_s)

// === Risk Management (2:1 R/R enforced) ===
long_stop = close - atr * atr_mult
long_target = close + (close - long_stop) * rr_ratio
short_stop = close + atr * atr_mult
short_target = close - (short_stop - close) * rr_ratio

if long_cond
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", stop=long_stop, limit=long_target)

if short_cond
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", stop=short_stop, limit=short_target)

// === Visual ===
plot(ema_f, "Fast EMA", color.blue, 2)
plot(ema_s, "Slow EMA", color.orange, 2)
plot(ema_t, "Trend EMA", color.gray, 1)
plotshape(long_cond, "Buy", shape.triangleup, location.belowbar, color.green, size=size.normal)
plotshape(short_cond, "Sell", shape.triangledown, location.abovebar, color.red, size=size.normal)

// Confluence display
var table t = table.new(position.top_right, 2, 1, bgcolor=color.new(color.black, 80))
if barstate.islast
    table.cell(t, 0, 0, "Bull: " + str.tostring(bull_score) + "/6", text_color=color.green)
    table.cell(t, 1, 0, "Bear: " + str.tostring(bear_score) + "/6", text_color=color.red)
"""


def _gen_ema_trend_pullback(params: dict, mgmt: dict) -> str:
    return f"""//@version=5
strategy("EMA Trend Pullback [Signal Forge]", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=2)

fast = input.int({params.get('ema_fast', 9)}, "Fast EMA")
slow = input.int({params.get('ema_slow', 21)}, "Slow EMA")
trend = input.int({params.get('ema_trend', 50)}, "Trend EMA")
rsi_len = input.int({params.get('rsi_period', 14)}, "RSI Period")
atr_len = input.int({params.get('atr_period', 14)}, "ATR Period")
atr_mult = input.float(1.5, "Stop ATR Mult", step=0.1)
pullback_mult = input.float(0.5, "Pullback ATR Zone", step=0.1)

ema_f = ta.ema(close, fast)
ema_s = ta.ema(close, slow)
ema_t = ta.ema(close, trend)
rsi = ta.rsi(close, rsi_len)
atr = ta.atr(atr_len)

// Stacked EMAs + pullback to slow EMA + RSI reset
long_trend = ema_f > ema_s and ema_s > ema_t
short_trend = ema_f < ema_s and ema_s < ema_t
pullback_buy = close <= ema_s + atr * pullback_mult and close > ema_t
pullback_sell = close >= ema_s - atr * pullback_mult and close < ema_t
rsi_reset_buy = rsi > 40 and rsi < 60
rsi_reset_sell = rsi > 40 and rsi < 60

long_cond = long_trend and pullback_buy and rsi_reset_buy and close > ema_f
short_cond = short_trend and pullback_sell and rsi_reset_sell and close < ema_f

long_stop = math.max(ema_t, close - atr * atr_mult)
long_tp = close + (close - long_stop) * {mgmt.get('target_1_r', 2.0)}
short_stop = math.min(ema_t, close + atr * atr_mult)
short_tp = close - (short_stop - close) * {mgmt.get('target_1_r', 2.0)}

if long_cond
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", stop=long_stop, limit=long_tp)
if short_cond
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", stop=short_stop, limit=short_tp)

plot(ema_f, "Fast", color.blue, 2)
plot(ema_s, "Slow", color.orange, 2)
plot(ema_t, "Trend", color.gray, 1)
plotshape(long_cond, "Buy", shape.triangleup, location.belowbar, color.green, size=size.small)
plotshape(short_cond, "Sell", shape.triangledown, location.abovebar, color.red, size=size.small)
"""


def _gen_donchian_breakout(params: dict, mgmt: dict) -> str:
    return """//@version=5
strategy("Donchian Breakout [Signal Forge]", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=2)

entry_len = input.int(20, "Entry Channel")
exit_len = input.int(10, "Exit Channel")
bb_len = input.int(20, "BB Period")
bb_mult = input.float(2.0, "BB StdDev")
min_vol = input.float(1.2, "Min Vol Ratio", step=0.1)
squeeze_bw = input.float(4.0, "Squeeze BW %", step=0.5)

upper = ta.highest(high, entry_len)
lower = ta.lowest(low, entry_len)
exit_upper = ta.highest(high, exit_len)
exit_lower = ta.lowest(low, exit_len)

[bb_mid, bb_up, bb_lo] = ta.bb(close, bb_len, bb_mult)
bw = (bb_up - bb_lo) / bb_mid * 100
was_squeeze = ta.lowest(bw, 5) < squeeze_bw
vol_ok = volume > ta.sma(volume, 20) * min_vol
strong_close = (close - low) / (high - low) > 0.75
weak_close = (close - low) / (high - low) < 0.25

long_cond = close >= upper and was_squeeze and strong_close
short_cond = close <= lower and was_squeeze and weak_close

if long_cond
    strategy.entry("Long", strategy.long)
if short_cond
    strategy.entry("Short", strategy.short)

// Turtle exit: exit on 10-day low/high
if strategy.position_size > 0 and close < exit_lower
    strategy.close("Long")
if strategy.position_size < 0 and close > exit_upper
    strategy.close("Short")

plot(upper, "20-High", color.new(color.green, 50))
plot(lower, "20-Low", color.new(color.red, 50))
bgcolor(bw < squeeze_bw ? color.new(color.yellow, 90) : na)
plotshape(long_cond, "Buy", shape.triangleup, location.belowbar, color.green)
plotshape(short_cond, "Sell", shape.triangledown, location.abovebar, color.red)
"""


def _gen_rsi2_momentum(params: dict, mgmt: dict) -> str:
    return """//@version=5
strategy("RSI(2) Momentum [Signal Forge]", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=2)

rsi_len = input.int(2, "RSI Period")
rsi_thresh = input.int(10, "RSI Threshold")
sma_trend = input.int(200, "Trend SMA")
sma_exit = input.int(5, "Exit SMA")
max_bars = input.int(5, "Max Hold Bars")

rsi2 = ta.rsi(close, rsi_len)
trend_filter = ta.sma(close, sma_trend)
exit_sma = ta.sma(close, sma_exit)

long_cond = close > trend_filter and rsi2 < rsi_thresh and low < low[1]
short_cond = close < trend_filter and rsi2 > (100 - rsi_thresh) and high > high[1]

if long_cond
    strategy.entry("Long", strategy.long)
if short_cond
    strategy.entry("Short", strategy.short)

// Exit: close above 5 SMA or time stop
bars_in = bar_index - strategy.opentrades.entry_bar_index(0)
if strategy.position_size > 0 and (close > exit_sma or bars_in >= max_bars)
    strategy.close("Long")
if strategy.position_size < 0 and (close < exit_sma or bars_in >= max_bars)
    strategy.close("Short")

plot(trend_filter, "200 SMA", color.gray, 1)
plot(exit_sma, "5 SMA", color.blue, 1)
bgcolor(rsi2 < rsi_thresh ? color.new(color.green, 90) : rsi2 > (100 - rsi_thresh) ? color.new(color.red, 90) : na)
plotshape(long_cond, "Buy", shape.triangleup, location.belowbar, color.green)
plotshape(short_cond, "Sell", shape.triangledown, location.abovebar, color.red)
"""


def _gen_pivot_bounce(params: dict, mgmt: dict) -> str:
    return f"""//@version=5
strategy("Pivot Bounce [Signal Forge]", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=2)

atr_len = input.int({params.get('atr_period', 14)}, "ATR Period")
atr_prox = input.float(0.3, "Proximity ATR Mult", step=0.1)
atr_stop = input.float(0.5, "Stop ATR Mult", step=0.1)
rsi_len = input.int({params.get('rsi_period', 14)}, "RSI Period")

atr = ta.atr(atr_len)
rsi = ta.rsi(close, rsi_len)

// Classic pivot points
pivot = (high[1] + low[1] + close[1]) / 3
s1 = 2 * pivot - high[1]
r1 = 2 * pivot - low[1]
s2 = pivot - (high[1] - low[1])
r2 = pivot + (high[1] - low[1])

near_s1 = math.abs(close - s1) <= atr * atr_prox
near_r1 = math.abs(close - r1) <= atr * atr_prox
bull_candle = close > open and (close - low) / (high - low) > 0.6
bear_candle = close < open and (high - close) / (high - low) > 0.6

long_cond = near_s1 and bull_candle and rsi < 50
short_cond = near_r1 and bear_candle and rsi > 50

if long_cond
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", stop=s1 - atr * atr_stop, limit=pivot)
if short_cond
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", stop=r1 + atr * atr_stop, limit=pivot)

plot(pivot, "Pivot", color.gray, style=plot.style_cross)
plot(s1, "S1", color.green, style=plot.style_cross)
plot(r1, "R1", color.red, style=plot.style_cross)
plotshape(long_cond, "Buy", shape.triangleup, location.belowbar, color.green)
plotshape(short_cond, "Sell", shape.triangledown, location.abovebar, color.red)
"""


def _gen_macd_divergence(params: dict, mgmt: dict) -> str:
    return f"""//@version=5
strategy("MACD Divergence [Signal Forge]", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=2)

fast = input.int({params.get('macd_fast', 12)}, "MACD Fast")
slow = input.int({params.get('macd_slow', 26)}, "MACD Slow")
sig = input.int({params.get('macd_signal', 9)}, "Signal")
atr_len = input.int({params.get('atr_period', 14)}, "ATR Period")
atr_mult = input.float(1.5, "Stop ATR Mult", step=0.1)
lookback = input.int(10, "Divergence Lookback")
rr = input.float({mgmt.get('target_1_r', 2.0)}, "R:R Ratio", step=0.1)

[macd_line, sig_line, hist] = ta.macd(close, fast, slow, sig)
atr = ta.atr(atr_len)

// Bullish divergence: price lower low + MACD higher low
price_ll = ta.lowest(low, lookback) < ta.lowest(low, lookback)[lookback]
macd_hl = ta.lowest(hist, lookback) > ta.lowest(hist, lookback)[lookback]
bull_div = price_ll and macd_hl and hist > hist[1]

// Bearish divergence: price higher high + MACD lower high
price_hh = ta.highest(high, lookback) > ta.highest(high, lookback)[lookback]
macd_lh = ta.highest(hist, lookback) < ta.highest(hist, lookback)[lookback]
bear_div = price_hh and macd_lh and hist < hist[1]

long_stop = close - atr * atr_mult
short_stop = close + atr * atr_mult

if bull_div
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", stop=long_stop, limit=close + (close - long_stop) * rr)
if bear_div
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", stop=short_stop, limit=close - (short_stop - close) * rr)

plotshape(bull_div, "Bull Div", shape.triangleup, location.belowbar, color.green, size=size.normal)
plotshape(bear_div, "Bear Div", shape.triangledown, location.abovebar, color.red, size=size.normal)
"""


def _gen_volatility_squeeze(params: dict, mgmt: dict) -> str:
    return f"""//@version=5
strategy("Volatility Squeeze [Signal Forge]", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=2)

bb_len = input.int({params.get('bb_period', 20)}, "BB Period")
bb_mult = input.float({params.get('bb_std', 2.0)}, "BB StdDev", step=0.1)
kc_len = input.int(20, "KC Period")
kc_mult = input.float(1.5, "KC Mult", step=0.1)
mom_len = input.int(12, "Momentum Period")

[bb_mid, bb_up, bb_lo] = ta.bb(close, bb_len, bb_mult)
kc_basis = ta.ema(close, kc_len)
kc_range = ta.atr(kc_len)
kc_up = kc_basis + kc_range * kc_mult
kc_lo = kc_basis - kc_range * kc_mult

// Squeeze: BB inside KC
squeeze = bb_lo > kc_lo and bb_up < kc_up
no_squeeze = not squeeze

// Momentum (linear regression)
mom = ta.linreg(close - ta.sma(close, bb_len), mom_len, 0)

// Signal: squeeze releases + momentum direction
long_cond = no_squeeze and squeeze[1] and mom > 0
short_cond = no_squeeze and squeeze[1] and mom < 0

atr = ta.atr({params.get('atr_period', 14)})

if long_cond
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", stop=bb_lo, limit=close + (close - bb_lo) * {mgmt.get('target_1_r', 2.0)})
if short_cond
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", stop=bb_up, limit=close - (bb_up - close) * {mgmt.get('target_1_r', 2.0)})

// Visual
bgcolor(squeeze ? color.new(color.orange, 85) : na)
plot(bb_up, "BB Upper", color.blue)
plot(bb_lo, "BB Lower", color.blue)
plot(kc_up, "KC Upper", color.red)
plot(kc_lo, "KC Lower", color.red)
plotshape(long_cond, "Buy", shape.triangleup, location.belowbar, color.green, size=size.normal)
plotshape(short_cond, "Sell", shape.triangledown, location.abovebar, color.red, size=size.normal)
"""


def list_strategies() -> list[dict]:
    """List available Pine Script strategies."""
    return [
        {"id": "ema_trend_pullback", "name": "EMA Trend Pullback",
         "description": "Buy pullbacks to 21 EMA in confirmed uptrend with stacked EMAs — the bread and butter of trend following"},
        {"id": "bollinger_squeeze", "name": "Bollinger Mean Reversion",
         "description": "Buy at lower BB / sell at upper BB in ranging markets with RSI and Stochastic confirmation"},
        {"id": "donchian_breakout", "name": "Donchian Breakout (Turtle)",
         "description": "Trade 20-day high/low breakouts from volatility squeezes — inspired by the Turtle Traders"},
        {"id": "rsi2_momentum", "name": "RSI(2) Momentum (Connors)",
         "description": "Buy extreme RSI(2) oversold dips above 200 SMA — Larry Connors' proven strategy"},
        {"id": "pivot_bounce", "name": "Pivot Point Bounce",
         "description": "Trade reversals at daily S1/R1 pivot levels with candle confirmation — floor trader method"},
        {"id": "macd_divergence", "name": "MACD Divergence",
         "description": "Spot when price makes new highs/lows but MACD doesn't confirm — classic divergence signal"},
        {"id": "volatility_squeeze", "name": "Volatility Squeeze (TTM)",
         "description": "BB squeezes inside Keltner Channels then breaks out — momentum release indicator"},
        {"id": "ema_crossover", "name": "EMA Crossover + RSI",
         "description": "Simple 9/21 EMA crossover filtered by RSI — good starting strategy for beginners"},
        {"id": "rsi_divergence", "name": "RSI Divergence + Pivots",
         "description": "RSI divergence combined with pivot point support/resistance"},
        {"id": "multi_confluence", "name": "Multi-Confluence (6 indicators)",
         "description": "Full 6-indicator confluence scoring — EMA, RSI, BB, Stochastic, MACD, trend filter"},
    ]
