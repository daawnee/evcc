<script setup>
defineProps({
  a: { type: Object, required: true }, // assumptions reactive object
})
</script>

<template>
  <details class="assumptions">
    <summary>Beállítások (futásteljesítmény és energiaárak)</summary>
    <div class="grid">
      <fieldset>
        <legend>Éves futásteljesítmény (km)</legend>
        <label class="field">
          <span>Ingázás (otthoni töltés / olcsó)</span>
          <input type="number" min="0" step="500" v-model.number="a.mileage.commute" />
        </label>
        <label class="field">
          <span>Utazás (gyorstöltés / autópálya)</span>
          <input type="number" min="0" step="500" v-model.number="a.mileage.travel" />
        </label>
      </fieldset>

      <fieldset>
        <legend>Olcsó tarifa (otthon / helyi)</legend>
        <label class="field"><span>Áram (Ft/kWh)</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_cheap.electricity" /></label>
        <label class="field"><span>Benzin (Ft/l)</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_cheap.petrol" /></label>
        <label class="field"><span>Dízel (Ft/l)</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_cheap.diesel" /></label>
      </fieldset>

      <fieldset>
        <legend>Drága tarifa (gyorstöltő / autópálya)</legend>
        <label class="field"><span>Áram (Ft/kWh)</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_expensive.electricity" /></label>
        <label class="field"><span>Benzin (Ft/l)</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_expensive.petrol" /></label>
        <label class="field"><span>Dízel (Ft/l)</span>
          <input type="number" min="0" step="1" v-model.number="a.energy_expensive.diesel" /></label>
      </fieldset>
    </div>
  </details>
</template>
