import { useSyncExternalStore } from 'react'

export interface LocalStore<T> {
  get: () => T
  set: (next: T) => void
  /** Re-renders whenever the value changes, in this tab or another. */
  use: () => T
}

/**
 * A value kept in localStorage that React components can subscribe to. `parse` turns whatever is
 * stored into a T, returning `fallback` for anything it doesn't recognise.
 */
export function createLocalStore<T>(key: string, fallback: T, parse: (raw: unknown) => T): LocalStore<T> {
  let cache: T | null = null
  const listeners = new Set<() => void>()

  function get(): T {
    if (cache === null) {
      try {
        const raw = localStorage.getItem(key)
        cache = raw ? parse(JSON.parse(raw)) : fallback
      } catch {
        cache = fallback
      }
    }
    return cache
  }

  function set(next: T) {
    cache = next
    try {
      localStorage.setItem(key, JSON.stringify(next))
    } catch {
      // Storage can be full or blocked; the value still works for this visit.
    }
    listeners.forEach((listener) => listener())
  }

  function subscribe(listener: () => void): () => void {
    listeners.add(listener)
    function onStorage(event: StorageEvent) {
      if (event.key === key) {
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

  return { get, set, use: () => useSyncExternalStore(subscribe, get) }
}
