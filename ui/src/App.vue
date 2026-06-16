<script setup>
import { reactive, ref, computed, onMounted, watch } from 'vue'
import CarPicker from './components/CarPicker.vue'
import AssumptionsPanel from './components/AssumptionsPanel.vue'
import TcoChart from './components/TcoChart.vue'
import { getModels, calculate } from './api.js'
import { fmtFt, fmtFtShort, monthsToYears } from './format.js'
import { t } from './i18n.js'

const HORIZON = 120 // months (fixed) — long enough to surface EV-vs-ICE break-evens

const models = ref([])
const loadError = ref('')

const carA = reactive({ entry: null, data: null, price: 0, ageMonths: 0 })
const carB = reactive({ entry: null, data: null, price: 0, ageMonths: 0 })

const assumptions = reactive({
  mileage: { commute: 13600, travel: 3400 },
  energy_cheap: { electricity: 72, petrol: 618.8, diesel: 642.1 },
  energy_expensive: { electricity: 225, petrol: 708.9, diesel: 722.9 },
  horizon_months: HORIZON,
})

const result = ref(null)
const calcError = ref('')
const loading = ref(false)

onMounted(async () => {
  try {
    models.value = await getModels()
  } catch (e) {
    loadError.value = String(e.message || e)
  }
})

const ready = computed(() => carA.entry && carB.entry && carA.price > 0 && carB.price > 0)

const names = computed(() => ({
  a: carA.entry ? `${carA.entry.make} ${carA.entry.model}` : 'A',
  b: carB.entry ? `${carB.entry.make} ${carB.entry.model}` : 'B',
}))

const breakeven = computed(() => result.value?.breakevens?.[0]?.month ?? null)

const summaryHtml = computed(() => {
  if (!result.value) return ''
  const [a, b] = result.value.cars
  const la = a.series[a.series.length - 1].cumulative
  const lb = b.series[b.series.length - 1].cumulative
  const cheaper = la < lb ? names.value.a : names.value.b
  const diff = Math.abs(la - lb)
  const horizonYears = Math.round(HORIZON / 12)
  const m = breakeven.value
  const head = m
    ? t.summaryCross(m, monthsToYears(m), cheaper)
    : t.summaryNoCross(horizonYears, cheaper)
  const diffLine = t.summaryDiff(horizonYears, fmtFtShort(diff), fmtFt(diff))
  return `${head}<div class="diff">${diffLine}</div>`
})

let timer = null
function scheduleRecompute() {
  clearTimeout(timer)
  timer = setTimeout(recompute, 300)
}

async function recompute() {
  if (!ready.value) {
    result.value = null
    return
  }
  loading.value = true
  calcError.value = ''
  try {
    result.value = await calculate({
      cars: [
        { model_id: carA.entry.model_id, purchase_price: carA.price, age_at_purchase_months: carA.ageMonths },
        { model_id: carB.entry.model_id, purchase_price: carB.price, age_at_purchase_months: carB.ageMonths },
      ],
      assumptions,
    })
  } catch (e) {
    calcError.value = String(e.message || e)
    result.value = null
  } finally {
    loading.value = false
  }
}

watch([carA, carB, assumptions], scheduleRecompute, { deep: true })
</script>

<template>
  <div class="app">
    <header class="topbar">
      <h1>{{ t.title }}</h1>
      <p class="sub">{{ t.subtitle }}</p>
    </header>

    <p v-if="loadError" class="error tile">{{ t.loadError }}: {{ loadError }}</p>

    <section class="pickers">
      <CarPicker :title="t.carA" accent="#2563eb" :models="models" :state="carA" />
      <CarPicker :title="t.carB" accent="#dc2626" :models="models" :state="carB" />
    </section>

    <AssumptionsPanel :a="assumptions" />

    <section class="results tile">
      <p v-if="!ready" class="hint">{{ t.hint }}</p>
      <p v-else-if="calcError" class="error">{{ t.calcError }}: {{ calcError }}</p>
      <template v-else-if="result">
        <div class="summary" v-html="summaryHtml"></div>
        <TcoChart :result="result" :names="names" :breakeven="breakeven" />
      </template>
    </section>

    <footer class="foot">{{ t.footer }}</footer>
  </div>
</template>
