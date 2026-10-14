from app.agent.executor import PaperExecutor
from app.agent.state import Portfolio
from app.strategies import Action, get_strategy
from app.strategies.base import Signal


def test_sma_cross_buys_on_golden_cross():
    # Flat, then one candle up: the fast average overtakes the slow one now.
    closes = [100.0] * 29 + [101.0]
    signal = get_strategy("sma_cross").evaluate("BTC/USDT", closes)
    assert signal.action == Action.BUY
    assert 0 < signal.confidence <= 1


def test_sma_cross_sees_a_cross_a_couple_of_candles_back():
    closes = [100.0] * 27 + [101.0, 103.0, 106.0]
    signal = get_strategy("sma_cross").evaluate("BTC/USDT", closes)
    assert signal.action == Action.BUY


def test_sma_cross_forgets_an_old_cross():
    closes = [100.0] * 25 + [101.0, 103.0, 106.0, 110.0, 115.0]
    signal = get_strategy("sma_cross").evaluate("BTC/USDT", closes)
    assert signal.action == Action.HOLD
    assert "alcista" in signal.reason


def test_sma_cross_sells_on_death_cross():
    closes = [100.0] * 29 + [99.0]
    signal = get_strategy("sma_cross").evaluate("BTC/USDT", closes)
    assert signal.action == Action.SELL


def test_sma_cross_holds_without_data():
    signal = get_strategy("sma_cross").evaluate("BTC/USDT", [100.0] * 5)
    assert signal.action == Action.HOLD
    assert "faltan velas" in signal.reason


def test_rsi_reversion_buys_oversold():
    closes = [float(v) for v in range(100, 70, -1)]
    signal = get_strategy("rsi_reversion").evaluate("ETH/USDT", closes)
    assert signal.action == Action.BUY
    assert signal.confidence == 1.0


def test_rsi_reversion_sells_overbought():
    closes = [float(v) for v in range(70, 100)]
    signal = get_strategy("rsi_reversion").evaluate("ETH/USDT", closes)
    assert signal.action == Action.SELL


def test_paper_executor_round_trip():
    portfolio = Portfolio(cash=1000.0)
    executor = PaperExecutor()
    buy = Signal(strategy="t", symbol="BTC/USDT", action=Action.BUY, confidence=1.0)
    trade = executor.execute(portfolio, buy, price=100.0, fraction=0.5)
    assert trade and trade.amount == 5.0
    assert portfolio.cash == 500.0
    assert portfolio.positions["BTC/USDT"].avg_price == 100.0

    sell = Signal(strategy="t", symbol="BTC/USDT", action=Action.SELL, confidence=1.0)
    trade = executor.execute(portfolio, sell, price=120.0, fraction=0.5)
    assert trade and trade.value == 600.0
    assert portfolio.cash == 1100.0
    assert "BTC/USDT" not in portfolio.positions
    assert len(portfolio.trades) == 2


def test_paper_executor_ignores_dust():
    portfolio = Portfolio(cash=20.0)
    buy = Signal(strategy="t", symbol="BTC/USDT", action=Action.BUY, confidence=1.0)
    assert PaperExecutor().execute(portfolio, buy, price=100.0, fraction=0.25) is None
    assert portfolio.cash == 20.0
