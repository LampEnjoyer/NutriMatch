import { useSyncExternalStore } from 'react'

import type { RecipeSummary } from '../api/types'

const STORAGE_KEY = 'nutrimatch.savedRecipes'

// Saved recipes live in this browser only; there are no user accounts yet.
let cache: RecipeSummary[] | null = null
const listeners = new Set<() => void>()

function read(): RecipeSummary[] {
  if (cache === null) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      const parsed: unknown = raw ? JSON.parse(raw) : []
      cache = Array.isArray(parsed) ? (parsed as RecipeSummary[]) : []
    } catch {
      cache = []
    }
  }
  return cache
}

function write(next: RecipeSummary[]) {
  cache = next
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // Storage can be full or blocked; the list still works for this visit.
  }
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  // Keep other tabs in sync.
  function onStorage(event: StorageEvent) {
    if (event.key === STORAGE_KEY) {
      cache = null
      listener()
    }
  }
  window.addEventListener('storage', onStorage)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('storage', onStorage)
  }
}

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
  const current = read()
  if (current.some((saved) => saved.id === recipe.id)) {
    write(current.filter((saved) => saved.id !== recipe.id))
  } else {
    write([toSummary(recipe), ...current])
  }
}

/** Newest first. Re-renders whenever the list changes. */
export function useSavedRecipes(): RecipeSummary[] {
  return useSyncExternalStore(subscribe, read)
}
