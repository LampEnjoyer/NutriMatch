import type { ReactNode } from 'react'

interface Props {
  kind: 'loading' | 'error' | 'empty'
  title: string
  children?: ReactNode
}

export function StatusMessage({ kind, title, children }: Props) {
  let role: 'status' | 'alert' = 'status'
  let titleClass = 'text-ink'
  if (kind === 'error') {
    role = 'alert'
    titleClass = 'text-tomato'
  }

  return (
    <div role={role} aria-live="polite" className="max-w-prose border-l-4 border-line py-2 pl-4">
      <p className={`font-semibold ${titleClass}`}>{title}</p>
      {children ? <div className="mt-1 font-serif text-meta">{children}</div> : null}
    </div>
  )
}
