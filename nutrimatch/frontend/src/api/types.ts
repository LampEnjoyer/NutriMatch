// Mirrors backend/app/schemas.py. Keep the two in sync.

export interface RecipeSummary {
  id: number
  slug: string
  title: string
  description: string | null
  cuisine: string | null
  meal_type: string | null
  preparation_time_min: number | null
  cooking_time_min: number | null
  inactive_time_min: number | null
  total_time_min: number | null
  servings: number
  image_url: string | null
}

export interface RecipeIngredient {
  ingredient_id: number
  name: string
  normalized_name: string
  quantity: number | null
  unit: string | null
  preparation_notes: string | null
  is_optional: boolean
  allergens: string[]
  animal_category: string
  // false: the allergens listed are not known to be complete
  allergens_reviewed: boolean
}

export interface RecipeDetail extends RecipeSummary {
  instructions: string[]
  source_name: string
  source_url: string | null
  ingredients_complete: boolean
  ingredients: RecipeIngredient[]
  // Ingredients with unverified allergen data; the user should check those labels.
  unreviewed_ingredients: string[]
  allergy_info_complete: boolean
}

export interface RecipeList {
  items: RecipeSummary[]
  total: number
}

export interface PreferenceOption {
  value: string
  label: string
}

export interface PreferenceQuestion {
  id: string
  label: string
  // Which Preferences field the answer lives in; `key` picks the entry inside nutrient_levels.
  field: 'nutrient_levels' | 'time_preference' | 'meal_types' | 'meal_size' | 'allergies'
  key: string | null
  type: 'single' | 'multi'
  options: PreferenceOption[]
  help: string | null
}

export interface PreferenceOptions {
  questions: PreferenceQuestion[]
}

/** What the user can change. The server replaces all of these on every save. */
export interface PreferencesInput {
  nutrient_levels: Record<string, string>
  time_preference: string | null
  meal_types: string[]
  meal_size: string | null
  allergies: string[]
}

export interface Preferences extends PreferencesInput {
  updated_at: string
}

export interface ScoreComponent {
  key: string
  score: number
  // false when this recipe had no data, so score is a neutral placeholder
  known: boolean
}

export interface RecommendationItem extends RecipeSummary {
  score: number
  components: ScoreComponent[]
  unreviewed_ingredients: string[]
  allergy_info_complete: boolean
}

export interface RecommendationList {
  items: RecommendationItem[]
  // recipes left after allergy filtering
  total: number
  excluded_for_allergies: number
  ranked_by: string[]
  ignored_preferences: string[]
}
