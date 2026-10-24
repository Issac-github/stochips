import { useEffect, useRef } from 'react'
import { init, use as registerCharts } from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsCoreOption } from 'echarts/core'
import { Empty } from 'antd'

registerCharts([
  BarChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  CanvasRenderer,
])

export function Chart({
  option,
  empty = false,
}: {
  option: EChartsCoreOption
  empty?: boolean
}) {
  const container = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (empty || !container.current) return
    const chart = init(container.current)
    chart.setOption(option)
    const observer = new ResizeObserver(() => chart.resize())
    observer.observe(container.current)
    return () => {
      observer.disconnect()
      chart.dispose()
    }
  }, [option, empty])
  return empty ? (
    <div className="chart-empty">
      <Empty description="当日暂无这项数据" />
    </div>
  ) : (
    <div
      ref={container}
      className="chart"
      role="img"
      aria-label="市场数据图表，完整数值见下方明细"
    />
  )
}

export function barOption(
  names: string[],
  values: number[],
  horizontal = false,
): EChartsCoreOption {
  const category = {
    type: 'category',
    data: names,
    axisTick: { show: false },
    axisLine: { show: false },
    axisLabel: {
      color: '#667085',
      width: horizontal ? 100 : 64,
      overflow: 'truncate',
    },
  }
  const value = {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#f0f2f7' } },
  }
  return {
    color: ['#3867eb'],
    tooltip: { trigger: 'axis', confine: true },
    grid: {
      top: 20,
      bottom: names.length > 12 ? 45 : 30,
      left: horizontal ? 112 : 40,
      right: 25,
    },
    xAxis: horizontal ? value : category,
    yAxis: horizontal ? { ...category, inverse: true } : value,
    dataZoom:
      names.length > 12
        ? [
            {
              type: 'slider',
              ...(horizontal
                ? { yAxisIndex: 0, right: 0 }
                : { xAxisIndex: 0, bottom: 0 }),
              start: 0,
              end: (100 * 12) / names.length,
            },
          ]
        : [],
    series: [
      {
        type: 'bar',
        data: values,
        barMaxWidth: 30,
        itemStyle: { borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0] },
        label: {
          show: true,
          position: horizontal ? 'right' : 'top',
          color: '#667085',
        },
      },
    ],
  }
}
