import type { Store } from '../api/types'

const UNIT_LABELS: Record<string, string> = {
  g: 'g',
  kg: 'kg',
  oz: 'oz',
  lb: 'lb',
  ml: 'ml',
  l: 'L',
  tsp: 'tsp',
  tbsp: 'tbsp',
  cup: 'cup',
  fl_oz: 'fl oz',
  piece: '',
  clove: 'clove',
  slice: 'slice',
  pinch: 'pinch',
}

const PLURAL_UNITS = new Set(['cup', 'clove', 'slice', 'pinch'])

export function formatMinutes(minutes: number | null): string {
  if (minutes === null) {
    return 'Time not listed'
  }
  if (minutes < 60) {
    return `${minutes} min`
  }
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (rest === 0) {
    return `${hours} hr`
  }
  return `${hours} hr ${rest} min`
}

/** Shows common fractions for cooking amounts (0.5 -> ½) and trims float noise. */
export function formatQuantity(quantity: number): string {
  const whole = Math.floor(quantity)
  const fraction = quantity - whole
  const fractions: [number, string][] = [
    [0.25, '¼'],
    [0.333, '⅓'],
    [0.5, '½'],
    [0.667, '⅔'],
    [0.75, '¾'],
  ]

  for (const [value, glyph] of fractions) {
    if (Math.abs(fraction - value) < 0.01) {
      if (whole === 0) {
        return glyph
      }
      return `${whole}${glyph}`
    }
  }

  if (Number.isInteger(quantity)) {
    return String(quantity)
  }
  return String(Math.round(quantity * 100) / 100)
}

export function formatAmount(quantity: number | null, unit: string | null): string {
  if (quantity === null || unit === null) {
    return 'To taste'
  }
  const amount = formatQuantity(quantity)
  let label = UNIT_LABELS[unit] ?? unit
  if (label === '') {
    return amount
  }
  if (quantity > 1 && PLURAL_UNITS.has(unit)) {
    label = `${label}s`
  }
  return `${amount} ${label}`
}

const USD = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

export function formatMoney(value: number): string {
  return USD.format(value)
}

/** "3:12 PM" for today, otherwise "Oct 22, 3:12 PM". */
export function formatFetchedAt(iso: string): string {
  const fetched = new Date(iso)
  const now = new Date()
  const time = fetched.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  if (fetched.toDateString() === now.toDateString()) {
    return time
  }
  const day = fetched.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return `${day}, ${time}`
}

export function storeAddress(store: Store): string {
  const parts: string[] = []
  if (store.address_line) {
    parts.push(store.address_line)
  }
  let cityLine = ''
  if (store.city) {
    cityLine = store.city
  }
  if (store.state) {
    if (cityLine === '') {
      cityLine = store.state
    } else {
      cityLine = `${cityLine}, ${store.state}`
    }
  }
  if (cityLine !== '') {
    parts.push(cityLine)
  }
  return parts.join(', ')
}

export function titleCase(value: string): string {
  if (value.length === 0) {
    return value
  }
  return value[0].toUpperCase() + value.slice(1)
}
