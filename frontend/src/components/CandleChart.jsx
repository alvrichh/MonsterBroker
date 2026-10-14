import { useEffect, useRef, useState } from 'react';
import { CandlestickSeries, HistogramSeries, LineSeries, createChart } from 'lightweight-charts';
import { useI18n } from '../i18n/I18nContext.jsx';
import { compact, money } from '../lib/format.js';
import { hexToRgba, sma } from '../lib/indicators.js';

// Candles + volume + SMA 9/21, on TradingView's Lightweight Charts (v5).
// Colours come from the CSS tokens so the chart follows the theme. Up
// candles are hollow and down candles filled: direction is readable without
// relying on green vs red alone.

const FAST = 9;
const SLOW = 21;

const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const readTheme = () => ({
  text: cssVar('--muted'),
  grid: cssVar('--rule'),
  up: cssVar('--up'),
  down: cssVar('--down'),
  fast: cssVar('--accent'),
  slow: cssVar('--series-2'),
  surface: cssVar('--bg-raised'),
  font: cssVar('--font-mono') || 'monospace',
});

const toBar = (c) => ({ time: Math.floor(c.time / 1000), open: c.open, high: c.high, low: c.low, close: c.close });
const volumeColor = (bar, colors) => hexToRgba(bar.close >= bar.open ? colors.up : colors.down, 0.45);
const lineData = (series, bars) => bars.map((b, i) => (series[i] === null ? null : { time: b.time, value: series[i] })).filter(Boolean);

export function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || 'dark');
  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(document.documentElement.dataset.theme || 'dark'));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);
  return theme;
}

export default function CandleChart({ candles = [], live = null, symbol, timeframe }) {
  const { t } = useI18n();
  const theme = useTheme();
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const closesRef = useRef([]);
  const [hover, setHover] = useState(null);

  // Build the chart once; React only feeds it data afterwards.
  useEffect(() => {
    const colors = readTheme();
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: { background: { type: 'solid', color: 'transparent' }, textColor: colors.text, fontFamily: colors.font, fontSize: 11 },
      grid: { vertLines: { color: colors.grid }, horzLines: { color: colors.grid } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
      crosshair: { mode: 0 },
      localization: { locale: 'es-ES', priceFormatter: (value) => money(value) },
    });
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: colors.surface, downColor: colors.down, borderVisible: true,
      borderUpColor: colors.up, borderDownColor: colors.down, wickUpColor: colors.up, wickDownColor: colors.down,
    });
    candleSeries.priceScale().applyOptions({ scaleMargins: { top: 0.06, bottom: 0.28 } });
    const volumeSeries = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: '', lastValueVisible: false, priceLineVisible: false });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    const lineOptions = { lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false };
    const fastSeries = chart.addSeries(LineSeries, { ...lineOptions, color: colors.fast });
    const slowSeries = chart.addSeries(LineSeries, { ...lineOptions, color: colors.slow });

    chart.subscribeCrosshairMove((param) => {
      const bar = param.time ? param.seriesData.get(candleSeries) : null;
      if (!bar) {
        setHover(null);
        return;
      }
      setHover({ ...bar, volume: param.seriesData.get(volumeSeries)?.value });
    });

    chartRef.current = chart;
    seriesRef.current = { candleSeries, volumeSeries, fastSeries, slowSeries };
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // History (and a theme change, which recolours the per-bar volume data).
  useEffect(() => {
    const chart = chartRef.current;
    const series = seriesRef.current;
    if (!chart || !series) return;
    const colors = readTheme();
    chart.applyOptions({ layout: { textColor: colors.text }, grid: { vertLines: { color: colors.grid }, horzLines: { color: colors.grid } } });
    series.candleSeries.applyOptions({ upColor: colors.surface, downColor: colors.down, borderUpColor: colors.up, borderDownColor: colors.down, wickUpColor: colors.up, wickDownColor: colors.down });
    series.fastSeries.applyOptions({ color: colors.fast });
    series.slowSeries.applyOptions({ color: colors.slow });

    if (!candles.length) return;
    const bars = candles.map(toBar);
    const closes = bars.map((b) => b.close);
    closesRef.current = closes;
    series.candleSeries.setData(bars);
    series.volumeSeries.setData(bars.map((b, i) => ({ time: b.time, value: candles[i].volume, color: volumeColor(b, colors) })));
    series.fastSeries.setData(lineData(sma(closes, FAST), bars));
    series.slowSeries.setData(lineData(sma(closes, SLOW), bars));
    chart.timeScale().fitContent();
  }, [candles, theme]);

  // The live candle from the WebSocket: same bar updates in place, a new one appends.
  useEffect(() => {
    const series = seriesRef.current;
    if (!series || !live || live.symbol !== symbol || live.interval !== timeframe || !closesRef.current.length) return;
    const colors = readTheme();
    const bar = { time: live.time, open: live.open, high: live.high, low: live.low, close: live.close };
    const lastBar = series.candleSeries.data().at(-1);
    if (lastBar && bar.time < lastBar.time) return; // older than what we have
    series.candleSeries.update(bar);
    series.volumeSeries.update({ time: bar.time, value: live.volume, color: volumeColor(bar, colors) });

    const closes = closesRef.current;
    if (lastBar && lastBar.time === bar.time) closes[closes.length - 1] = bar.close;
    else closes.push(bar.close);
    const fast = sma(closes.slice(-FAST), FAST).at(-1);
    const slow = sma(closes.slice(-SLOW), SLOW).at(-1);
    if (fast !== null) series.fastSeries.update({ time: bar.time, value: fast });
    if (slow !== null) series.slowSeries.update({ time: bar.time, value: slow });
  }, [live, symbol, timeframe]);

  const last = candles.at(-1);
  const shown = hover || (last && { ...toBar(last), volume: last.volume });
  const up = shown ? shown.close >= shown.open : true;

  return (
    <div className="chart">
      <div className="chart__legend mono" aria-live="off">
        {shown ? (
          <>
            <span><em>{t('chart.open')}</em> {money(shown.open)}</span>
            <span><em>{t('chart.high')}</em> {money(shown.high)}</span>
            <span><em>{t('chart.low')}</em> {money(shown.low)}</span>
            <span className={up ? 'up' : 'down'}><em>{t('chart.close')}</em> {money(shown.close)}</span>
            <span><em>{t('chart.volume')}</em> {compact(shown.volume)}</span>
          </>
        ) : <span className="muted">{t('chart.loading')}</span>}
        <span className="chart__keys">
          <i className="chart__key chart__key--fast" /> SMA {FAST}
          <i className="chart__key chart__key--slow" /> SMA {SLOW}
        </span>
      </div>
      <div className="chart__canvas" ref={containerRef} />
    </div>
  );
}
