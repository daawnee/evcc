<script setup>
import { t } from '../i18n.js'

defineProps({
  a: { type: Object, required: true }, // assumptions reactive object
})
</script>

<template>
  <details class="assumptions tile">
    <summary>{{ t.assumptionsTitle }}</summary>
    <div class="grid">
      <fieldset>
        <legend>{{ t.annualMileage }}</legend>
        <label class="field">
          <span>{{ t.commute }}</span>
          <input type="number" min="0" step="500" v-model.number="a.mileage.commute" />
        </label>
        <label class="field">
          <span>{{ t.travel }}</span>
          <input type="number" min="0" step="500" v-model.number="a.mileage.travel" />
        </label>
      </fieldset>

      <fieldset>
        <legend>{{ t.cheapTariff }}</legend>
        <label class="field"><span>{{ t.electricity }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_cheap.electricity" /></label>
        <label class="field"><span>{{ t.petrol }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_cheap.petrol" /></label>
        <label class="field"><span>{{ t.diesel }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_cheap.diesel" /></label>
      </fieldset>

      <fieldset>
        <legend>{{ t.expensiveTariff }}</legend>
        <label class="field"><span>{{ t.electricity }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_expensive.electricity" /></label>
        <label class="field"><span>{{ t.petrol }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_expensive.petrol" /></label>
        <label class="field"><span>{{ t.diesel }}</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_expensive.diesel" /></label>
      </fieldset>

      <fieldset>
        <legend>{{ t.priceIncrease }}</legend>
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
      </fieldset>
    </div>
  </details>
</template>
