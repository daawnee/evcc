<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { fmtFt } from '../format.js'

Chart.register(LineController, LineElement, PointElement, LinearScale, Tooltip, Legend, Filler)

const props = defineProps({
  result: Object,
  names: Object, // { a, b }
  breakeven: Number, // month or null
})

const COLOR_A = '#2563eb'
const COLOR_B = '#dc2626'

const canvas = ref(null)
let chart = null

// Draws a dashed vertical line + label at the break-even month.
const breakevenPlugin = {
  id: 'breakeven',
  afterDraw(c) {
    const m = c.$breakeven
    if (!m) return
    const x = c.scales.x.getPixelForValue(m)
    const { top, bottom } = c.chartArea
    const ctx = c.ctx
    ctx.save()
    ctx.strokeStyle = '#10b981'
    ctx.lineWidth = 1.5
    ctx.setLineDash([5, 4])
    ctx.beginPath()
    ctx.moveTo(x, top)
    ctx.lineTo(x, bottom)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = '#10b981'
    ctx.font = '600 12px system-ui, sans-serif'
    ctx.textAlign = x > (c.chartArea.left + c.chartArea.right) / 2 ? 'right' : 'left'
    ctx.fillText(`megtérülés: ${m}. hó`, x + (ctx.textAlign === 'right' ? -6 : 6), top + 14)
    ctx.restore()
  },
}

function build() {
  if (!props.result || !canvas.value) return
  const [ca, cb] = props.result.cars
  const ds = (car, color) => ({
    label: '',
    data: car.series.map((p) => ({ x: p.month, y: p.cumulative })),
    borderColor: color,
    backgroundColor: color,
    borderWidth: 2,
    pointRadius: 0,
    tension: 0.15,
  })
  const datasets = [
    { ...ds(ca, COLOR_A), label: props.names.a },
    { ...ds(cb, COLOR_B), label: props.names.b },
  ]

  if (chart) chart.destroy()
  chart = new Chart(canvas.value, {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          type: 'linear',
          title: { display: true, text: 'Birtoklás (hónap)' },
          ticks: { stepSize: 12 },
        },
        y: {
          title: { display: true, text: 'Kumulált költség (Ft)' },
          ticks: { callback: (v) => (v / 1_000_000).toLocaleString('hu-HU') + ' M' },
        },
      },
      plugins: {
        legend: { labels: { usePointStyle: true } },
        tooltip: {
          callbacks: {
            title: (items) => `${items[0].parsed.x}. hónap`,
            label: (item) => `${item.dataset.label}: ${fmtFt(item.parsed.y)}`,
          },
        },
      },
    },
    plugins: [breakevenPlugin],
  })
  chart.$breakeven = props.breakeven
  chart.update()
}

onMounted(build)
watch(() => props.result, build)
watch(
  () => props.breakeven,
  (m) => {
    if (chart) {
      chart.$breakeven = m
      chart.update()
    }
  }
)
onBeforeUnmount(() => chart && chart.destroy())
</script>

<template>
  <div class="chart-box">
    <canvas ref="canvas"></canvas>
  </div>
</template>
