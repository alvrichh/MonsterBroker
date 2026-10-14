"""Parsers for Binance USDT-M futures payloads (shaped like the real ones)
and the quarterly basis arithmetic."""

import pytest

from app.services.futures import (
    FUNDING_PERIODS_PER_YEAR,
    is_usdt_perp,
    parse_funding,
    parse_klines,
    parse_oi_history,
    parse_premium,
    parse_quarterly,
    parse_ratios,
    parse_taker,
    parse_ticker,
)

PREMIUM = {"symbol": "BTCUSDT", "markPrice": "83757.97", "indexPrice": "83805.24", "estimatedSettlePrice": "83834.9",
           "lastFundingRate": "0.00010000", "interestRate": "0.00010000", "nextFundingTime": 1791964800000,
           "time": 1791949867000}

FUNDING = [{"symbol": "BTCUSDT", "fundingTime": 1791907200000, "fundingRate": "0.00003455", "markPrice": "83393.3"},
           {"symbol": "BTCUSDT", "fundingTime": 1791936000001, "fundingRate": "-0.00001022", "markPrice": "83125.7"}]

OI_HIST = [{"symbol": "BTCUSDT", "sumOpenInterest": "91861.774", "sumOpenInterestValue": "7650625143.37",
            "timestamp": 1791943200000}]

RATIOS = [{"symbol": "BTCUSDT", "longAccount": "0.5697", "longShortRatio": "1.3240", "shortAccount": "0.4303",
           "timestamp": 1791943200000}]

TAKER = [{"buySellRatio": "1.6639", "sellVol": "1336.582", "buyVol": "2223.887", "timestamp": 1791943200000}]

TICKER = {"symbol": "BTCUSDT", "lastPrice": "83752.70", "priceChangePercent": "0.585", "highPrice": "84134.20",
          "lowPrice": "82912.80", "quoteVolume": "9993075657.76", "volume": "119720.983"}

KLINE = [[1791946800000, "83608.40", "83942.10", "83606.40", "83752.70", "5307.298", 1791950399999, "4.4e8", 104221,
          "2982.6", "2.4e8", "0"]]

SYMBOLS = [
    {"symbol": "BTCUSDT_261225", "pair": "BTCUSDT", "contractType": "CURRENT_QUARTER", "status": "TRADING",
     "deliveryDate": 1798185600000},
    {"symbol": "BTCUSDT_270326", "pair": "BTCUSDT", "contractType": "NEXT_QUARTER", "status": "TRADING",
     "deliveryDate": 1806048000000},
    {"symbol": "BTCUSDT", "pair": "BTCUSDT", "contractType": "PERPETUAL", "status": "TRADING", "deliveryDate": 0},
    {"symbol": "OLDUSDT_250926", "pair": "OLDUSDT", "contractType": "CURRENT_QUARTER", "status": "SETTLING",
     "deliveryDate": 1790000000000},
]


def test_parse_premium_annualizes_funding():
    p = parse_premium(PREMIUM)
    assert p.mark_price == 83757.97 and p.index_price == 83805.24
    assert p.funding_rate == 0.0001
    assert p.funding_annualized == pytest.approx(0.0001 * FUNDING_PERIODS_PER_YEAR)


def test_parse_funding_and_oi_and_ratios():
    assert [f.rate for f in parse_funding(FUNDING)] == [0.00003455, -0.00001022]
    oi = parse_oi_history(OI_HIST)[0]
    assert oi.contracts == 91861.774 and oi.value == 7650625143.37
    ratio = parse_ratios(RATIOS)[0]
    assert ratio.long + ratio.short == pytest.approx(1.0) and ratio.ratio == 1.324
    taker = parse_taker(TAKER)[0]
    assert taker.ratio == 1.6639 and taker.buy > taker.sell


def test_parse_ticker_and_klines():
    t = parse_ticker(TICKER)
    assert t.change_24h == 0.585 and t.volume_24h == 9993075657.76
    c = parse_klines(KLINE)[0]
    assert (c.time, c.open, c.close, c.volume) == (1791946800000, 83608.4, 83752.7, 5307.298)


def test_is_usdt_perp():
    assert is_usdt_perp("BTCUSDT") and not is_usdt_perp("BTCUSDT_261225") and not is_usdt_perp("BTCUSD_PERP")


def test_parse_quarterly_basis():
    premiums = {
        "BTCUSDT_261225": parse_premium({**PREMIUM, "symbol": "BTCUSDT_261225", "markPrice": "84643.29"}),
        "BTCUSDT_270326": parse_premium({**PREMIUM, "symbol": "BTCUSDT_270326", "markPrice": "86000"}),
    }
    now_ms = 1798185600000 - 73 * 86_400_000  # 73 days before the December delivery
    rows = parse_quarterly(SYMBOLS, premiums, now_ms)
    assert [r.symbol for r in rows] == ["BTCUSDT_261225", "BTCUSDT_270326"]  # perp and settling dropped
    dec = rows[0]
    assert dec.delivery_date == "2026-12-25" and dec.days_to_delivery == 73.0
    assert dec.basis == pytest.approx((84643.29 / 83805.24 - 1) * 100)
    assert dec.annualized_basis == pytest.approx(dec.basis * 365 / 73)
