import { useState } from 'react'

import { getPricingStatus, getRecipeCost } from '../api/client'
import type { PricingStatus, RecipeCost } from '../api/types'
import { useAsync } from './useAsync'

export interface RecipePricing {
  status: PricingStatus
  cost: RecipeCost | null
  costError: string | null
}

/** Loads pricing status, then the recipe's cost when a store is chosen. Call refresh() after changing store. */
export function useRecipePricing(recipeId: number) {
  const [version, setVersion] = useState(0)

  const state = useAsync<RecipePricing>(async () => {
    const status = await getPricingStatus()
    if (!status.configured || status.store === null) {
      return { status, cost: null, costError: null }
    }
    try {
      const cost = await getRecipeCost(recipeId)
      return { status, cost, costError: null }
    } catch (error) {
      let message = 'Prices did not load.'
      if (error instanceof Error) {
        message = error.message
      }
      return { status, cost: null, costError: message }
    }
  }, [recipeId, version])

  function refresh() {
    setVersion(version + 1)
  }

  return { state, refresh }
}
