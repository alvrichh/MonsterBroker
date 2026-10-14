"""Technical indicators over plain lists of closes.

Every function returns a list as long as its input, with None while the
indicator is warming up, so a series lines up with the candles it came from.
No pandas: the series here are a few hundred points at most.
"""

from __future__ import annotations

from statistics import pstdev

Series = list[float | None]


def sma(values: list[float], period: int) -> Series:
    out: Series = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    window = sum(values[:period])
    out[period - 1] = window / period
    for i in range(period, len(values)):
        window += values[i] - values[i - period]
        out[i] = window / period
    return out


def ema(values: list[float], period: int) -> Series:
    out: Series = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    k = 2 / (period + 1)
    current = sum(values[:period]) / period
    out[period - 1] = current
    for i in range(period, len(values)):
        current = values[i] * k + current * (1 - k)
        out[i] = current
    return out


def rsi(values: list[float], period: int = 14) -> Series:
    """Wilder's RSI, 0-100."""
    out: Series = [None] * len(values)
    if period <= 0 or len(values) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        delta = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(delta, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0.0)) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def macd(values: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[Series, Series, Series]:
    """Returns (macd line, signal line, histogram)."""
    fast_ema, slow_ema = ema(values, fast), ema(values, slow)
    line: Series = [f - s if f is not None and s is not None else None for f, s in zip(fast_ema, slow_ema, strict=True)]
    known = [v for v in line if v is not None]
    offset = len(line) - len(known)
    signal_line: Series = [None] * offset + ema(known, signal)
    hist: Series = [m - s if m is not None and s is not None else None for m, s in zip(line, signal_line, strict=True)]
    return line, signal_line, hist


def bollinger(values: list[float], period: int = 20, width: float = 2.0) -> tuple[Series, Series, Series]:
    """Returns (upper, middle, lower)."""
    middle = sma(values, period)
    upper: Series = [None] * len(values)
    lower: Series = [None] * len(values)
    for i in range(period - 1, len(values)):
        deviation = pstdev(values[i - period + 1 : i + 1]) * width
        upper[i] = middle[i] + deviation  # type: ignore[operator]
        lower[i] = middle[i] - deviation  # type: ignore[operator]
    return upper, middle, lower


def latest(series: Series) -> float | None:
    for value in reversed(series):
        if value is not None:
            return value
    return None


def snapshot(closes: list[float]) -> dict[str, float | None]:
    """The usual indicators at the last candle, for the API and the agent."""
    macd_line, macd_signal, macd_hist = macd(closes)
    bb_upper, bb_mid, bb_lower = bollinger(closes)
    return {
        "price": closes[-1] if closes else None,
        "sma_9": latest(sma(closes, 9)),
        "sma_21": latest(sma(closes, 21)),
        "sma_50": latest(sma(closes, 50)),
        "ema_12": latest(ema(closes, 12)),
        "ema_26": latest(ema(closes, 26)),
        "rsi_14": latest(rsi(closes, 14)),
        "macd": latest(macd_line),
        "macd_signal": latest(macd_signal),
        "macd_hist": latest(macd_hist),
        "bb_upper": latest(bb_upper),
        "bb_mid": latest(bb_mid),
        "bb_lower": latest(bb_lower),
    }
