import { useState } from 'react'
import type { FormEvent } from 'react'

import { searchStores, setStore } from '../api/client'
import type { Store } from '../api/types'
import { storeAddress } from '../lib/format'

interface Props {
  onSaved: () => void
}

export function StorePicker({ onSaved }: Props) {
  const [zip, setZip] = useState('')
  const [stores, setStores] = useState<Store[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSearch(event: FormEvent) {
    event.preventDefault()
    if (!/^\d{5}$/.test(zip)) {
      setError('Enter a 5-digit ZIP code.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const found = await searchStores(zip)
      setStores(found)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Store search failed.')
    } finally {
      setBusy(false)
    }
  }

  async function handleChoose(store: Store) {
    setBusy(true)
    setError(null)
    try {
      await setStore(store.location_id)
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Saving the store failed.')
      setBusy(false)
    }
  }

  return (
    <div>
      <form onSubmit={handleSearch} className="flex gap-2">
        <label htmlFor="store-zip" className="sr-only">
          ZIP code
        </label>
        <input
          id="store-zip"
          inputMode="numeric"
          autoComplete="postal-code"
          maxLength={5}
          placeholder="ZIP code"
          value={zip}
          onChange={(event) => setZip(event.target.value.trim())}
          className="w-28 border border-ink px-2 py-1.5 tabular-nums"
        />
        <button
          type="submit"
          disabled={busy}
          className="bg-basil px-3 py-1.5 font-semibold text-white hover:bg-basil-dark disabled:opacity-60"
        >
          Find stores
        </button>
      </form>

      {error ? (
        <p role="alert" className="mt-2 text-sm text-tomato">
          {error}
        </p>
      ) : null}

      {stores !== null && stores.length === 0 ? (
        <p className="mt-3 text-sm text-meta">
          No Kroger-family stores near {zip}. Kroger doesn't operate everywhere; try a ZIP code in a state it serves.
        </p>
      ) : null}

      {stores !== null && stores.length > 0 ? (
        <ul className="mt-3 divide-y divide-line border-y border-line">
          {stores.map((store) => (
            <li key={store.location_id}>
              <button
                type="button"
                disabled={busy}
                onClick={() => handleChoose(store)}
                className="w-full py-2 text-left hover:bg-line/40 disabled:opacity-60"
              >
                <span className="block font-semibold">{store.name}</span>
                <span className="block text-sm text-meta">{storeAddress(store)}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
