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

// --- Store pricing ---

export interface Store {
  provider: string
  location_id: string
  name: string
  chain: string | null
  address_line: string | null
  city: string | null
  state: string | null
  zip_code: string | null
}

export interface PricingStatus {
  configured: boolean
  provider: string
  store: Store | null
}

export interface PricedProduct {
  description: string
  brand: string | null
  size_text: string | null
  package_price: number
  regular_price: number | null
  promo_price: number | null
  on_sale: boolean
  sold_by_weight: boolean
  product_url: string | null
  image_url: string | null
  fetched_at: string
}

export type LineCostStatus = 'priced' | 'not_purchased' | 'unmeasured' | 'no_match' | 'needs_conversion'

export interface LineCost {
  position: number
  ingredient_id: number
  name: string
  quantity: number | null
  unit: string | null
  status: LineCostStatus
  reason: string | null
  is_pantry_staple: boolean
  product: PricedProduct | null
  used_cost: number | null
  packages: number | null
  shopping_cost: number | null
}

export interface RecipeCost {
  recipe_id: number
  servings: number
  currency: string
  store: Store
  recipe_cost: number
  cost_per_serving: number
  shopping_total: number
  pantry_staples_cost: number
  unpriced_count: number
  is_complete: boolean
  oldest_price_at: string | null
  lines: LineCost[]
}
