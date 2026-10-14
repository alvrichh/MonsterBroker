import { useEffect, useRef, useState } from 'react';
import { AreaSeries, createChart } from 'lightweight-charts';
import { usd } from '../lib/format.js';
import { hexToRgba } from '../lib/indicators.js';
import { useTheme } from './CandleChart.jsx';

// One series over time (daily points, 'YYYY-MM-DD'): a 2px line with a 10%
// wash underneath, crosshair readout handed back through onHover.
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export default function AreaChart({ points = [], onHover }) {
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
      timeScale: { borderVisible: false },
      crosshair: { mode: 0, vertLine: { labelVisible: true }, horzLine: { visible: false, labelVisible: false } },
      localization: { locale: 'es-ES', priceFormatter: (value) => usd(value, 0) },
    });
    const series = chart.addSeries(AreaSeries, { lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerRadius: 4 });
    chart.subscribeCrosshairMove((param) => {
      const point = param.time ? param.seriesData.get(series) : null;
      onHover?.(point ? { date: param.time, value: point.value } : null);
    });
    chartRef.current = chart;
    seriesRef.current = series;
    setReady(true);
    return () => chart.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!ready || !chartRef.current) return;
    const accent = cssVar('--accent');
    chartRef.current.applyOptions({ layout: { textColor: cssVar('--muted') }, grid: { horzLines: { color: cssVar('--rule') } } });
    seriesRef.current.applyOptions({ lineColor: accent, topColor: hexToRgba(accent, 0.25), bottomColor: hexToRgba(accent, 0.02) });
    if (points.length) {
      seriesRef.current.setData(points.map((p) => ({ time: p.date, value: p.value })));
      chartRef.current.timeScale().fitContent();
    }
  }, [points, theme, ready]);

  return <div className="chart__canvas chart__canvas--short" ref={containerRef} />;
}
