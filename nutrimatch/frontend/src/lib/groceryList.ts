import type { RecipeDetail } from '../api/types'
import { formatAmount } from './format'
import { createLocalStore } from './localStore'

export interface GroceryRecipe {
  id: number
  title: string
}

interface GroceryState {
  recipes: GroceryRecipe[]
  // Keys of the combined items the user has ticked off (see GroceryItem.key).
  checked: string[]
}

const EMPTY: GroceryState = { recipes: [], checked: [] }

const store = createLocalStore<GroceryState>('nutrimatch.groceryList', EMPTY, (raw) => {
  const value = raw as Partial<GroceryState> | null
  if (!value || !Array.isArray(value.recipes) || !Array.isArray(value.checked)) {
    return EMPTY
  }
  return { recipes: value.recipes, checked: value.checked }
})

export const useGroceryList = store.use

/** Adds the recipe to the grocery list, or removes it if it's already there. */
export function toggleGroceryRecipe(recipe: GroceryRecipe) {
  const current = store.get()
  if (current.recipes.some((item) => item.id === recipe.id)) {
    store.set({ ...current, recipes: current.recipes.filter((item) => item.id !== recipe.id) })
  } else {
    store.set({ ...current, recipes: [...current.recipes, { id: recipe.id, title: recipe.title }] })
  }
}

export function toggleChecked(key: string) {
  const current = store.get()
  const checked = current.checked.includes(key)
    ? current.checked.filter((item) => item !== key)
    : [...current.checked, key]
  store.set({ ...current, checked })
}

export function uncheckAll() {
  store.set({ ...store.get(), checked: [] })
}

export function clearGroceryList() {
  store.set(EMPTY)
}

export interface GroceryItem {
  key: string
  name: string
  // One entry per unit, e.g. ["2 cups", "1 tbsp"]; amounts in different units aren't converted.
  amounts: string[]
  toTaste: boolean
  // True only when every recipe that uses it marks it optional.
  optional: boolean
  recipes: string[]
}

/** Merges the ingredient lines of several recipes into one list, summing amounts that share a unit. */
export function combineIngredients(recipes: RecipeDetail[]): GroceryItem[] {
  const byIngredient = new Map<
    number,
    { name: string; totals: Map<string, number>; toTaste: boolean; optional: boolean; recipes: Set<string> }
  >()

  for (const recipe of recipes) {
    for (const line of recipe.ingredients) {
      let entry = byIngredient.get(line.ingredient_id)
      if (!entry) {
        entry = { name: line.name, totals: new Map(), toTaste: false, optional: true, recipes: new Set() }
        byIngredient.set(line.ingredient_id, entry)
      }
      if (line.quantity === null || line.unit === null) {
        entry.toTaste = true
      } else {
        entry.totals.set(line.unit, (entry.totals.get(line.unit) ?? 0) + line.quantity)
      }
      entry.optional = entry.optional && line.is_optional
      entry.recipes.add(recipe.title)
    }
  }

  const items: GroceryItem[] = []
  for (const [ingredientId, entry] of byIngredient) {
    items.push({
      key: String(ingredientId),
      name: entry.name,
      amounts: [...entry.totals].map(([unit, quantity]) => formatAmount(quantity, unit)),
      toTaste: entry.toTaste && entry.totals.size === 0,
      optional: entry.optional,
      recipes: [...entry.recipes],
    })
  }
  return items.sort((a, b) => a.name.localeCompare(b.name))
}
