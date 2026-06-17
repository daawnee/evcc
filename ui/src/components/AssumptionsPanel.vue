<script setup>
import { ref, computed } from 'vue'
import { t } from '../i18n.js'

defineProps({
  a: { type: Object, required: true }, // assumptions reactive object
})

const TABS = [
  { key: 'mileage', label: t.tabs.mileage, caption: t.annualMileage },
  { key: 'cheap', label: t.tabs.cheap, caption: t.cheapTariff },
  { key: 'expensive', label: t.tabs.expensive, caption: t.expensiveTariff },
  { key: 'inflation', label: t.tabs.inflation, caption: t.priceIncrease },
]
const active = ref('mileage')
const caption = computed(() => TABS.find((x) => x.key === active.value).caption)
</script>

<template>
  <details class="assumptions tile">
    <summary>{{ t.assumptionsTitle }}</summary>

    <div class="tabs">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        type="button"
        class="tab"
        :class="{ active: active === tab.key }"
        @click="active = tab.key"
      >{{ tab.label }}</button>
    </div>

    <div class="tab-caption">{{ caption }}</div>

    <div class="tab-fields">
      <template v-if="active === 'mileage'">
        <label class="field"><span>{{ t.commute }}</span>
          <input type="number" min="0" step="500" v-model.number="a.mileage.commute" /></label>
        <label class="field"><span>{{ t.travel }}</span>
          <input type="number" min="0" step="500" v-model.number="a.mileage.travel" /></label>
      </template>

      <template v-else-if="active === 'cheap'">
        <label class="field"><span>{{ t.electricity }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_cheap.electricity" /></label>
        <label class="field"><span>{{ t.petrol }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_cheap.petrol" /></label>
        <label class="field"><span>{{ t.diesel }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_cheap.diesel" /></label>
      </template>

      <template v-else-if="active === 'expensive'">
        <label class="field"><span>{{ t.electricity }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_expensive.electricity" /></label>
        <label class="field"><span>{{ t.petrol }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_expensive.petrol" /></label>
        <label class="field"><span>{{ t.diesel }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_expensive.diesel" /></label>
      </template>

      <template v-else-if="active === 'inflation'">
        <label class="field"><span>{{ t.inflElectricity }}</span>
          <input type="number" min="0" step="0.5"
            :value="(a.energy_inflation.electricity * 100).toFixed(1)"
            @input="a.energy_inflation.electricity = (Number($event.target.value) || 0) / 100" /></label>
        <label class="field"><span>{{ t.inflPetrol }}</span>
          <input type="number" min="0" step="0.5"
            :value="(a.energy_inflation.petrol * 100).toFixed(1)"
            @input="a.energy_inflation.petrol = (Number($event.target.value) || 0) / 100" /></label>
        <label class="field"><span>{{ t.inflDiesel }}</span>
          <input type="number" min="0" step="0.5"
            :value="(a.energy_inflation.diesel * 100).toFixed(1)"
            @input="a.energy_inflation.diesel = (Number($event.target.value) || 0) / 100" /></label>
      </template>
    </div>
  </details>
</template>
