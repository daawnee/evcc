<script setup>
import { reactive, ref, computed, onMounted, watch } from 'vue'
import CarPicker from './components/CarPicker.vue'
import AssumptionsPanel from './components/AssumptionsPanel.vue'
import TcoChart from './components/TcoChart.vue'
import { getModels, calculate } from './api.js'
import { fmtFt, fmtFtShort, monthsToYears } from './format.js'

const HORIZON = 120 // months (fixed) — long enough to surface EV-vs-ICE break-evens

const models = ref([])
const loadError = ref('')

const carA = reactive({ entry: null, data: null, price: 0, ageMonths: 12 })
const carB = reactive({ entry: null, data: null, price: 0, ageMonths: 12 })

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

const ready = computed(
  () => carA.entry && carB.entry && carA.price > 0 && carB.price > 0
)

const names = computed(() => ({
  a: carA.entry ? `${carA.entry.make} ${carA.entry.model}` : 'A',
  b: carB.entry ? `${carB.entry.make} ${carB.entry.model}` : 'B',
}))

const breakeven = computed(() => result.value?.breakevens?.[0]?.month ?? null)

const summary = computed(() => {
  if (!result.value) return null
  const [a, b] = result.value.cars
  const la = a.series[a.series.length - 1].cumulative
  const lb = b.series[b.series.length - 1].cumulative
  const cheaper = la < lb ? names.value.a : names.value.b
  const diff = Math.abs(la - lb)
  const m = breakeven.value
  return { m, cheaper, diff, horizonYears: Math.round(HORIZON / 12) }
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
      <h1>EV TCO Kalkulátor</h1>
      <p class="sub">Két autó teljes birtoklási költségének összehasonlítása</p>
    </header>

    <p v-if="loadError" class="error">Hiba a modellek betöltésekor: {{ loadError }}</p>

    <section class="pickers">
      <CarPicker title="Autó A" accent="#2563eb" :models="models" :state="carA" />
      <CarPicker title="Autó B" accent="#dc2626" :models="models" :state="carB" />
    </section>

    <AssumptionsPanel :a="assumptions" />

    <section class="results">
      <p v-if="!ready" class="hint">
        Válassz ki két autót és add meg a vételárakat az összehasonlításhoz.
      </p>
      <p v-else-if="calcError" class="error">Számítási hiba: {{ calcError }}</p>
      <template v-else-if="result">
        <div class="summary">
          <template v-if="summary.m">
            A két görbe a <strong>{{ summary.m }}. hónapban</strong>
            ({{ monthsToYears(summary.m) }} év) találkozik.
            Ezen túl tartva <strong>{{ summary.cheaper }}</strong> a jobb választás.
          </template>
          <template v-else>
            A görbék {{ summary.horizonYears }} év alatt nem keresztezik egymást —
            végig <strong>{{ summary.cheaper }}</strong> az olcsóbb.
          </template>
          <div class="diff">
            {{ summary.horizonYears }} év alatt a különbség
            <strong>{{ fmtFtShort(summary.diff) }}</strong> ({{ fmtFt(summary.diff) }}).
          </div>
        </div>
        <TcoChart :result="result" :names="names" :breakeven="breakeven" />
      </template>
    </section>

    <footer class="foot">
      Az adatok tájékoztató jellegűek. Energia- és fenntartási árak: magyar piac, alapértelmezett értékek.
    </footer>
  </div>
</template>
