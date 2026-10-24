import { NavLink, Outlet } from 'react-router'

const NAV_ITEMS = [
  { to: '/', label: 'Discover', end: true },
  { to: '/saved', label: 'Saved' },
  { to: '/grocery', label: 'Grocery list' },
  { to: '/settings', label: 'Settings' },
]

function navClass({ isActive }: { isActive: boolean }): string {
  const base = 'whitespace-nowrap border-b-2 px-1 py-3 text-[15px]'
  if (isActive) {
    return `${base} border-ink font-semibold text-ink`
  }
  return `${base} border-transparent text-meta hover:text-ink`
}

export function AppShell() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 pt-4 sm:flex-row sm:items-end sm:justify-between sm:gap-8 sm:px-6">
          <NavLink to="/" className="pb-1 text-2xl font-black tracking-tight [font-stretch:85%] sm:pb-3">
            NutriMatch
          </NavLink>
          <nav aria-label="Main" className="-mx-1 flex gap-5 overflow-x-auto">
            {NAV_ITEMS.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={navClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        <Outlet />
      </main>
    </div>
  )
}
