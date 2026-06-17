// Language selection: default English. Hungarian (`hu`) is used only when a `hu-XX` locale appears
// in the browser's language list before any `en-XX` locale; otherwise fall back to English.
function pickLang() {
  const langs =
    (typeof navigator !== 'undefined' && (navigator.languages || [navigator.language])) || []
  for (const l of langs) {
    const low = String(l || '').toLowerCase()
    if (low.startsWith('hu')) return 'hu'
    if (low.startsWith('en')) return 'en'
  }
  return 'en'
}

const messages = {
  en: {
    title: 'EV TCO Calculator',
    subtitle: 'Compare the total cost of ownership of two cars',
    carA: 'Car A',
    carB: 'Car B',
    searchFirst: 'Search make / model…',
    searchAnother: 'Search another car…',
    all: 'All',
    moreResults: (n) => `+${n} more — type to narrow`,
    purchasePrice: 'Purchase price (Ft)',
    ageAtPurchase: 'Age at purchase',
    kmRange: 'km range',
    plusElectric: '+ electric',
    loadError: 'Error loading models',
    calcError: 'Calculation error',
    hint: 'Select two cars and enter purchase prices to compare.',
    assumptionsTitle: 'Settings (mileage and energy prices)',
    tabs: { mileage: 'Mileage', cheap: 'Cheap tariff', expensive: 'Expensive tariff', inflation: 'Price increase' },
    annualMileage: 'Annual mileage (km)',
    commute: 'Commute (home charging / cheap)',
    travel: 'Travel (fast charging / highway)',
    cheapTariff: 'Cheap tariff (home / local)',
    expensiveTariff: 'Expensive tariff (fast charger / highway)',
    electricity: 'Electricity (Ft/kWh)',
    petrol: 'Petrol (Ft/l)',
    diesel: 'Diesel (Ft/l)',
    priceIncrease: 'Yearly price increase (%/yr)',
    inflElectricity: 'Electricity',
    inflPetrol: 'Petrol',
    inflDiesel: 'Diesel',
    chartX: 'Ownership (months)',
    chartY: 'Cumulative cost (Ft)',
    breakeven: (m) => `break-even: month ${m}`,
    tooltipMonth: (m) => `month ${m}`,
    footer:
      'Figures are indicative. Energy and running-cost prices: Hungarian market, default values.',
    types: { bev: 'Electric', petrol: 'Petrol', diesel: 'Diesel', hybrid: 'Hybrid', phev: 'Plug-in hybrid' },
    age: { asNew: 'As new', year: 'year', years: 'years', month: 'month', months: 'months' },
    summaryCross: (m, years, cheaper) =>
      `The two curves cross at <strong>month ${m}</strong> (${years} years). Keep it longer than that and <strong>${cheaper}</strong> is the better choice.`,
    summaryNoCross: (horizonYears, cheaper) =>
      `The curves don't cross within ${horizonYears} years — <strong>${cheaper}</strong> is cheaper throughout.`,
    summaryDiff: (horizonYears, shortStr, fullStr) =>
      `Over ${horizonYears} years the difference is <strong>${shortStr}</strong> (${fullStr}).`,
  },
  hu: {
    title: 'EV TCO Kalkulátor',
    subtitle: 'Két autó teljes birtoklási költségének összehasonlítása',
    carA: 'Autó A',
    carB: 'Autó B',
    searchFirst: 'Keresés márka / modell…',
    searchAnother: 'Másik autó keresése…',
    all: 'Összes',
    moreResults: (n) => `+${n} további — szűkíts gépeléssel`,
    purchasePrice: 'Vételár (Ft)',
    ageAtPurchase: 'Életkor vásárláskor',
    kmRange: 'km hatótáv',
    plusElectric: '+ elektromos',
    loadError: 'Hiba a modellek betöltésekor',
    calcError: 'Számítási hiba',
    hint: 'Válassz ki két autót és add meg a vételárakat az összehasonlításhoz.',
    assumptionsTitle: 'Beállítások (futásteljesítmény és energiaárak)',
    tabs: { mileage: 'Futásteljesítmény', cheap: 'Olcsó tarifa', expensive: 'Drága tarifa', inflation: 'Áremelkedés' },
    annualMileage: 'Éves futásteljesítmény (km)',
    commute: 'Ingázás (otthoni töltés / olcsó)',
    travel: 'Utazás (gyorstöltés / autópálya)',
    cheapTariff: 'Olcsó tarifa (otthon / helyi)',
    expensiveTariff: 'Drága tarifa (gyorstöltő / autópálya)',
    electricity: 'Áram (Ft/kWh)',
    petrol: 'Benzin (Ft/l)',
    diesel: 'Dízel (Ft/l)',
    priceIncrease: 'Éves áremelkedés (%/év)',
    inflElectricity: 'Áram',
    inflPetrol: 'Benzin',
    inflDiesel: 'Dízel',
    chartX: 'Birtoklás (hónap)',
    chartY: 'Kumulált költség (Ft)',
    breakeven: (m) => `megtérülés: ${m}. hó`,
    tooltipMonth: (m) => `${m}. hónap`,
    footer:
      'Az adatok tájékoztató jellegűek. Energia- és fenntartási árak: magyar piac, alapértelmezett értékek.',
    types: { bev: 'Elektromos', petrol: 'Benzin', diesel: 'Dízel', hybrid: 'Hibrid', phev: 'Plug-in hibrid' },
    age: { asNew: 'Újként', year: 'év', years: 'év', month: 'hónap', months: 'hónap' },
    summaryCross: (m, years, cheaper) =>
      `A két görbe a <strong>${m}. hónapban</strong> (${years} év) keresztezi egymást. Ezen túl tartva <strong>${cheaper}</strong> a jobb választás.`,
    summaryNoCross: (horizonYears, cheaper) =>
      `A görbék ${horizonYears} év alatt nem keresztezik egymást — végig <strong>${cheaper}</strong> az olcsóbb.`,
    summaryDiff: (horizonYears, shortStr, fullStr) =>
      `${horizonYears} év alatt a különbség <strong>${shortStr}</strong> (${fullStr}).`,
  },
}

export const lang = pickLang()
export const t = messages[lang]
export const locale = lang === 'hu' ? 'hu-HU' : 'en-US'

if (typeof document !== 'undefined') document.documentElement.lang = lang
