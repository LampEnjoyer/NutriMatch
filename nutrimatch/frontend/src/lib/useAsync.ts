import { useEffect, useState } from 'react'

export type AsyncState<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: T }

/** Runs `load` whenever `deps` change and tracks loading / error / ready. Ignores stale responses. */
export function useAsync<T>(load: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ status: 'loading' })

  // Callers pass their own dependency list, which the linter can't see through.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })

    load().then(
      (data) => {
        if (!cancelled) {
          setState({ status: 'ready', data })
        }
      },
      (error: unknown) => {
        if (!cancelled) {
          let message = 'Something went wrong.'
          if (error instanceof Error) {
            message = error.message
          }
          setState({ status: 'error', message })
        }
      },
    )

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
