import type { PreferencesInput, RecommendationItem } from '../api/types'
import { titleCase } from './format'

// A component at or above this score is shown to the user as a strong match. Presentation only:
// the server ranks by the scores themselves.
const STRONG_MATCH = 0.7

const PREFERENCE_NAMES: Record<string, string> = {
  protein: 'protein',
  fat: 'fat',
  calories: 'calories',
  time: 'time to make',
  meal_type: 'meal type',
  meal_size: 'serving size',
}

export function preferenceName(key: string): string {
  return PREFERENCE_NAMES[key] ?? key
}

function chipLabel(key: string, recipe: RecommendationItem, preferences: PreferencesInput): string | null {
  switch (key) {
    case 'protein':
    case 'fat':
    case 'calories': {
      const level = preferences.nutrient_levels[key]
      return level === 'high' || level === 'low' ? `${titleCase(level)} ${key}` : null
    }
    case 'time':
      return preferences.time_preference ? `${titleCase(preferences.time_preference)} time` : null
    case 'meal_type':
      return recipe.meal_type ? `Good for ${recipe.meal_type}` : null
    case 'meal_size':
      return preferences.meal_size === 'solo' ? 'Solo-sized' : preferences.meal_size === 'family' ? 'Family-sized' : null
    default:
      return null
  }
}

/** Short labels for the preferences this recipe matches well. Unknown data never produces a chip. */
export function matchChips(recipe: RecommendationItem, preferences: PreferencesInput): string[] {
  const chips: string[] = []
  for (const component of recipe.components) {
    if (component.known && component.score >= STRONG_MATCH) {
      const label = chipLabel(component.key, recipe, preferences)
      if (label) {
        chips.push(label)
      }
    }
  }
  return chips
}
