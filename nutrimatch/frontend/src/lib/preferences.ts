import type { PreferenceQuestion, Preferences, PreferencesInput } from '../api/types'

export const NO_PREFERENCE = 'no_preference'

export const EMPTY_PREFERENCES: PreferencesInput = {
  nutrient_levels: {},
  time_preference: null,
  meal_types: [],
  meal_size: null,
  allergies: [],
}

/** The editable part of what the server returns (drops updated_at). */
export function toInput(preferences: Preferences | PreferencesInput): PreferencesInput {
  return {
    nutrient_levels: { ...preferences.nutrient_levels },
    time_preference: preferences.time_preference,
    meal_types: [...preferences.meal_types],
    meal_size: preferences.meal_size,
    allergies: [...preferences.allergies],
  }
}

/** True when the question already has a "don't care" choice, so the form needn't add one. */
export function offersNoPreference(question: PreferenceQuestion): boolean {
  return question.options.some((option) => option.value === NO_PREFERENCE)
}

/** The selected value of a single-choice question, or null when nothing is chosen. */
export function singleAnswer(preferences: PreferencesInput, question: PreferenceQuestion): string | null {
  switch (question.field) {
    case 'nutrient_levels':
      return question.key ? (preferences.nutrient_levels[question.key] ?? null) : null
    case 'time_preference':
      return preferences.time_preference
    case 'meal_size':
      return preferences.meal_size
    default:
      return null
  }
}

export function multiAnswer(preferences: PreferencesInput, question: PreferenceQuestion): string[] {
  switch (question.field) {
    case 'meal_types':
      return preferences.meal_types
    case 'allergies':
      return preferences.allergies
    default:
      return []
  }
}

/** Returns a copy with the question answered. null (or "don't care" for a nutrient) clears it. */
export function withSingleAnswer(
  preferences: PreferencesInput,
  question: PreferenceQuestion,
  value: string | null,
): PreferencesInput {
  const next = toInput(preferences)
  switch (question.field) {
    case 'nutrient_levels':
      if (question.key) {
        if (value === null || value === NO_PREFERENCE) {
          delete next.nutrient_levels[question.key]
        } else {
          next.nutrient_levels[question.key] = value
        }
      }
      break
    case 'time_preference':
      next.time_preference = value
      break
    case 'meal_size':
      next.meal_size = value
      break
  }
  return next
}

/** Returns a copy with `value` added to or removed from a multi-choice question. */
export function withToggledAnswer(
  preferences: PreferencesInput,
  question: PreferenceQuestion,
  value: string,
): PreferencesInput {
  const next = toInput(preferences)
  const list = question.field === 'meal_types' ? next.meal_types : question.field === 'allergies' ? next.allergies : null
  if (list === null) {
    return next
  }
  const at = list.indexOf(value)
  if (at === -1) {
    list.push(value)
  } else {
    list.splice(at, 1)
  }
  return next
}

function normalised(preferences: PreferencesInput): string {
  const levels = Object.entries(preferences.nutrient_levels)
    .filter(([, level]) => level !== NO_PREFERENCE)
    .sort(([a], [b]) => a.localeCompare(b))
  return JSON.stringify([
    levels,
    preferences.time_preference,
    [...preferences.meal_types].sort(),
    preferences.meal_size,
    [...preferences.allergies].sort(),
  ])
}

/** Compares what the user means, so "don't care" and an unset nutrient are the same. */
export function samePreferences(a: PreferencesInput, b: PreferencesInput): boolean {
  return normalised(a) === normalised(b)
}
