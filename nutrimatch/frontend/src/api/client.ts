import type {
  PreferenceOptions,
  Preferences,
  PreferencesInput,
  RecipeDetail,
  RecipeList,
  RecommendationList,
} from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, init)
  } catch {
    throw new ApiError(0, "Can't reach the NutriMatch server. Check that the backend is running.")
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`
    try {
      const body = await response.json()
      if (body && typeof body.detail === 'string') {
        message = body.detail
      }
    } catch {
      // Body wasn't JSON; keep the generic message.
    }
    throw new ApiError(response.status, message)
  }

  return (await response.json()) as T
}

export function listRecipes(limit = 50, offset = 0): Promise<RecipeList> {
  return request<RecipeList>(`/recipes?limit=${limit}&offset=${offset}`)
}

export function getRecipe(id: number): Promise<RecipeDetail> {
  return request<RecipeDetail>(`/recipes/${id}`)
}

export function getRecommendations(limit = 20, offset = 0): Promise<RecommendationList> {
  return request<RecommendationList>(`/recommendations?limit=${limit}&offset=${offset}`)
}

export function getPreferenceOptions(): Promise<PreferenceOptions> {
  return request<PreferenceOptions>('/preferences/options')
}

export function getPreferences(): Promise<Preferences> {
  return request<Preferences>('/preferences')
}

export function savePreferences(preferences: PreferencesInput): Promise<Preferences> {
  return request<Preferences>('/preferences', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(preferences),
  })
}
