import pytest

from app.tools.indicators import bollinger, ema, latest, macd, rsi, sma, snapshot


def test_sma_warmup_and_values():
    assert sma([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]


def test_sma_short_series_is_all_none():
    assert sma([1, 2], 3) == [None, None]


def test_ema_starts_from_sma():
    series = ema([1, 2, 3, 4, 5], 3)
    assert series[:2] == [None, None]
    assert series[2] == 2.0
    assert series[3] == pytest.approx(3.0)


def test_rsi_is_100_on_a_straight_climb():
    closes = list(range(1, 20))
    assert latest(rsi(closes, 14)) == 100.0


def test_rsi_is_0_on_a_straight_fall():
    closes = list(range(20, 1, -1))
    assert latest(rsi(closes, 14)) == 0.0


def test_rsi_stays_in_range_on_noise():
    closes = [100 + (i % 5) * (-1) ** i for i in range(60)]
    values = [v for v in rsi(closes) if v is not None]
    assert values and all(0 <= v <= 100 for v in values)


def test_macd_lengths_match_input():
    closes = [float(i) for i in range(60)]
    line, signal, hist = macd(closes)
    assert len(line) == len(signal) == len(hist) == 60
    assert latest(hist) is not None


def test_bollinger_bands_surround_middle():
    closes = [10.0, 11, 12, 11, 10, 9, 10, 11, 12, 13, 12, 11, 10, 11, 12, 13, 14, 13, 12, 11, 10]
    upper, middle, lower = bollinger(closes, period=20)
    assert lower[-1] < middle[-1] < upper[-1]


def test_snapshot_has_every_key():
    values = snapshot([float(100 + i) for i in range(60)])
    assert values["price"] == 159.0
    for key in ("sma_9", "sma_21", "rsi_14", "macd", "bb_upper"):
        assert values[key] is not None
