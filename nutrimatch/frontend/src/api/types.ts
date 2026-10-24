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
}

export interface RecipeDetail extends RecipeSummary {
  instructions: string[]
  source_name: string
  source_url: string | null
  ingredients_complete: boolean
  ingredients: RecipeIngredient[]
}

export interface RecipeList {
  items: RecipeSummary[]
  total: number
}
