import { useEffect, useRef, useState } from 'react';
import { HistogramSeries, createChart } from 'lightweight-charts';
import { useTheme } from './CandleChart.jsx';

// Bars around a zero baseline (funding rate): positive in the up colour,
// negative in the down colour. points: [{ time, value }], time in unix seconds.
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export default function HistogramChart({ points = [], formatter = (v) => v.toFixed(4), onHover }) {
  const theme = useTheme();
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: { background: { type: 'solid', color: 'transparent' }, textColor: cssVar('--muted'), fontFamily: cssVar('--font-mono'), fontSize: 11 },
      grid: { vertLines: { visible: false }, horzLines: { color: cssVar('--rule') } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
      crosshair: { mode: 0, horzLine: { visible: false, labelVisible: false } },
      localization: { locale: 'es-ES', priceFormatter: formatter },
    });
    const series = chart.addSeries(HistogramSeries, { base: 0, priceLineVisible: false, lastValueVisible: false });
    chart.subscribeCrosshairMove((param) => {
      const point = param.time ? param.seriesData.get(series) : null;
      onHover?.(point ? { time: param.time, value: point.value } : null);
    });
    chartRef.current = chart;
    seriesRef.current = series;
    setReady(true);
    return () => chart.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!ready || !chartRef.current) return;
    const up = cssVar('--up');
    const down = cssVar('--down');
    chartRef.current.applyOptions({ layout: { textColor: cssVar('--muted') }, grid: { horzLines: { color: cssVar('--rule') } } });
    if (points.length) {
      seriesRef.current.setData(points.map((p) => ({ time: p.time, value: p.value, color: p.value >= 0 ? up : down })));
      chartRef.current.timeScale().fitContent();
    }
  }, [points, theme, ready]);

  return <div className="chart__canvas chart__canvas--short" ref={containerRef} />;
}
