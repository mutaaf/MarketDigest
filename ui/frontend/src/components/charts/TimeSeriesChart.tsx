import { useEffect, useRef } from 'react'
import { createChart, IChartApi, HistogramSeries, type HistogramData, type Time } from 'lightweight-charts'

interface HistogramBar {
  time: string
  value: number
  color?: string
}

interface TimeSeriesChartProps {
  data: HistogramBar[]
  height?: number
  positiveColor?: string
  negativeColor?: string
  className?: string
}

export default function TimeSeriesChart({
  data,
  height = 200,
  positiveColor = '#22c55e',
  negativeColor = '#ef4444',
  className = '',
}: TimeSeriesChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: 'transparent' },
        textColor: '#9ca3af',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(0,0,0,0.04)' },
        horzLines: { color: 'rgba(0,0,0,0.04)' },
      },
      rightPriceScale: {
        borderVisible: false,
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        horzLine: { visible: false },
      },
    })

    const series = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
    })

    const chartData: HistogramData<Time>[] = data.map(d => ({
      time: d.time as Time,
      value: d.value,
      color: d.color || (d.value >= 0 ? positiveColor : negativeColor),
    }))

    series.setData(chartData)
    chart.timeScale().fitContent()
    chartRef.current = chart

    const resizeObserver = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    })
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [data, height, positiveColor, negativeColor])

  return <div ref={containerRef} className={className} />
}
