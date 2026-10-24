import { useState } from 'react'

import { formatFetchedAt, formatMoney, storeAddress } from '../lib/format'
import type { useRecipePricing } from '../lib/useRecipePricing'
import { StorePicker } from './StorePicker'

interface Props {
  pricing: ReturnType<typeof useRecipePricing>
}

export function CostPanel({ pricing }: Props) {
  const [changingStore, setChangingStore] = useState(false)
  const { state, refresh } = pricing

  function handleSaved() {
    setChangingStore(false)
    refresh()
  }

  let body = null

  if (state.status === 'loading') {
    body = <p className="text-meta">Looking up store prices…</p>
  } else if (state.status === 'error') {
    body = (
      <p role="alert" className="text-tomato">
        {state.message}
      </p>
    )
  } else if (!state.data.status.configured) {
    body = (
      <p className="font-serif text-meta">
        Store prices are off. Add a Kroger client ID and secret to the backend's .env file to turn them on.
      </p>
    )
  } else if (state.data.status.store === null || changingStore) {
    body = (
      <>
        <p className="mb-3 font-serif text-meta">Pick a Kroger-family store to price this recipe's ingredients.</p>
        <StorePicker onSaved={handleSaved} />
        {changingStore ? (
          <button type="button" onClick={() => setChangingStore(false)} className="mt-3 text-sm text-meta underline">
            Keep current store
          </button>
        ) : null}
      </>
    )
  } else {
    const store = state.data.status.store
    const cost = state.data.cost

    body = (
      <>
        {state.data.costError ? (
          <p role="alert" className="text-tomato">
            {state.data.costError}
          </p>
        ) : null}

        {cost ? (
          <dl>
            <div className="flex items-baseline justify-between border-b border-ink py-1">
              <dt className="font-semibold">This recipe</dt>
              <dd className="label-numeral text-2xl">{formatMoney(cost.recipe_cost)}</dd>
            </div>
            <div className="flex items-baseline justify-between border-b border-ink py-1">
              <dt className="font-semibold">Per serving</dt>
              <dd className="label-numeral text-lg">{formatMoney(cost.cost_per_serving)}</dd>
            </div>
            <div className="flex items-baseline justify-between py-1">
              <dt className="font-semibold">Shopping total</dt>
              <dd className="label-numeral text-lg">{formatMoney(cost.shopping_total)}</dd>
            </div>
          </dl>
        ) : null}

        {cost ? (
          <div className="mt-2 space-y-1 font-serif text-sm text-meta">
            <p>
              "This recipe" counts only the share of each package you use. "Shopping total" is the whole packages you'd
              buy. Pantry staples like salt and pepper are left out of both.
            </p>
            {!cost.is_complete ? (
              <p className="text-tomato">
                {cost.unpriced_count === 1
                  ? '1 ingredient couldn’t be priced, so these totals are low.'
                  : `${cost.unpriced_count} ingredients couldn’t be priced, so these totals are low.`}
              </p>
            ) : null}
          </div>
        ) : null}

        <p className="mt-3 text-sm text-meta">
          Prices from {store.name}
          {storeAddress(store) ? `, ${storeAddress(store)}` : ''}
          {cost && cost.oldest_price_at ? `, as of ${formatFetchedAt(cost.oldest_price_at)}` : ''}.{' '}
          <button type="button" onClick={() => setChangingStore(true)} className="underline">
            Change store
          </button>
        </p>
      </>
    )
  }

  return (
    <section aria-labelledby="cost-heading" className="mt-6 border-2 border-ink p-3">
      <h2 id="cost-heading" className="border-b-8 border-ink pb-1 text-2xl leading-none label-numeral">
        Cost at the store
      </h2>
      <div className="mt-2">{body}</div>
    </section>
  )
}
