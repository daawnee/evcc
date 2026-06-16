<script setup>
import { ref, computed } from 'vue'
import { getCar, photoUrl, EUR_HUF } from '../api.js'
import { TYPE_LABEL, ageLabel } from '../format.js'
import { t } from '../i18n.js'

const props = defineProps({
  title: String,
  accent: String,
  models: { type: Array, default: () => [] },
  state: { type: Object, required: true }, // { entry, data, price, ageMonths }
})

const search = ref('')
const open = ref(false)

const matches = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return props.models.slice(0, 30)
  return props.models
    .filter((m) => (m.make + ' ' + m.model).toLowerCase().includes(q))
    .slice(0, 30)
})

// Age dropdown: 0 ("As new") .. 180 months (15 years).
const ageOptions = Array.from({ length: 181 }, (_, i) => i)

async function pick(entry) {
  props.state.entry = entry
  open.value = false
  search.value = ''
  props.state.data = await getCar(entry.model_id)
  const p = props.state.data?.price_new
  if (p && (p.DE_EUR || p.NL_EUR)) {
    props.state.price = Math.round((p.DE_EUR || p.NL_EUR) * EUR_HUF)
  } else if (!props.state.price) {
    props.state.price = 0
  }
}

function clear() {
  props.state.entry = null
  props.state.data = null
}

const specLine = computed(() => {
  const d = props.state.data
  if (!d) return ''
  const s = d.specs || {}
  if (d.type === 'bev') {
    const parts = []
    if (s.battery_kwh) parts.push(`${s.battery_kwh} kWh`)
    if (s.range_real_km) parts.push(`${s.range_real_km} ${t.kmRange}`)
    parts.push(`${d.consumption.average} kWh/100km`)
    return parts.join(' · ')
  }
  const unit = d.type === 'phev' ? `L/100km ${t.plusElectric}` : 'L/100km'
  return `${d.consumption.average}–${d.consumption.highway} ${unit}`
})
</script>

<template>
  <div class="picker tile" :style="{ '--accent': accent }">
    <div class="picker-title">{{ title }}</div>

    <div class="search-wrap">
      <input
        class="search"
        type="text"
        :placeholder="state.entry ? t.searchAnother : t.searchFirst"
        v-model="search"
        @focus="open = true"
        @input="open = true"
      />
      <ul v-if="open && matches.length" class="search-results">
        <li v-for="m in matches" :key="m.model_id" @mousedown.prevent="pick(m)">
          <img v-if="m.photo" :src="photoUrl(m.model_id)" alt="" loading="lazy" />
          <span v-else class="noimg" />
          <span class="r-name">{{ m.make }} {{ m.model }}</span>
          <span class="r-type">{{ TYPE_LABEL[m.type] || m.type }}</span>
        </li>
      </ul>
    </div>

    <div v-if="state.entry" class="card">
      <img v-if="state.entry.photo" :src="photoUrl(state.entry.model_id)" class="hero" alt="" />
      <div class="card-body">
        <div class="card-head">
          <strong>{{ state.entry.make }} {{ state.entry.model }}</strong>
          <button class="link" @click="clear">✕</button>
        </div>
        <div class="badge">{{ TYPE_LABEL[state.entry.type] || state.entry.type }}</div>
        <div class="spec">{{ specLine }}</div>

        <label class="field">
          <span>{{ t.purchasePrice }}</span>
          <input type="number" min="0" step="100000" v-model.number="state.price" />
        </label>
        <label class="field">
          <span>{{ t.ageAtPurchase }}</span>
          <select v-model.number="state.ageMonths">
            <option v-for="n in ageOptions" :key="n" :value="n">{{ ageLabel(n) }}</option>
          </select>
        </label>
      </div>
    </div>
  </div>
</template>
