import type { RecipeSummary } from '../api/types'
import { createLocalStore } from './localStore'

// Saved recipes live in this browser only; there are no user accounts yet.
const store = createLocalStore<RecipeSummary[]>('nutrimatch.savedRecipes', [], (raw) =>
  Array.isArray(raw) ? (raw as RecipeSummary[]) : [],
)

/** Keeps only the summary fields, so a RecipeDetail doesn't drag its ingredients into storage. */
function toSummary(recipe: RecipeSummary): RecipeSummary {
  return {
    id: recipe.id,
    slug: recipe.slug,
    title: recipe.title,
    description: recipe.description,
    cuisine: recipe.cuisine,
    meal_type: recipe.meal_type,
    preparation_time_min: recipe.preparation_time_min,
    cooking_time_min: recipe.cooking_time_min,
    inactive_time_min: recipe.inactive_time_min,
    total_time_min: recipe.total_time_min,
    servings: recipe.servings,
    image_url: recipe.image_url,
  }
}

/** Adds the recipe to the top of the list, or removes it if it's already there. */
export function toggleSaved(recipe: RecipeSummary) {
  const current = store.get()
  if (current.some((saved) => saved.id === recipe.id)) {
    store.set(current.filter((saved) => saved.id !== recipe.id))
  } else {
    store.set([toSummary(recipe), ...current])
  }
}

/** Newest first. Re-renders whenever the list changes. */
export const useSavedRecipes = store.use
