import { Link } from 'react-router'

import { listRecipes } from '../api/client'
import type { RecipeSummary } from '../api/types'
import { StatusMessage } from '../components/StatusMessage'
import { formatMinutes, titleCase } from '../lib/format'
import { useAsync } from '../lib/useAsync'

function RecipeRow({ recipe }: { recipe: RecipeSummary }) {
  const facts: string[] = []
  if (recipe.cuisine) {
    facts.push(titleCase(recipe.cuisine))
  }
  if (recipe.meal_type) {
    facts.push(titleCase(recipe.meal_type))
  }
  facts.push(`Serves ${recipe.servings}`)

  return (
    <li className="border-b border-line py-5 first:pt-0">
      <Link to={`/recipes/${recipe.id}`} className="group grid gap-x-8 gap-y-2 sm:grid-cols-[1fr_9rem]">
        <div>
          <h2 className="text-xl font-bold leading-snug group-hover:underline">{recipe.title}</h2>
          {recipe.description ? (
            <p className="mt-1 max-w-[65ch] font-serif text-[17px] leading-relaxed text-meta">{recipe.description}</p>
          ) : null}
          <p className="mt-2 text-sm text-meta">{facts.join(', ')}</p>
        </div>
        <div className="sm:text-right">
          <p className="label-numeral text-2xl leading-none">{formatMinutes(recipe.total_time_min)}</p>
          {recipe.inactive_time_min ? (
            <p className="mt-1 text-sm text-tomato">+ {formatMinutes(recipe.inactive_time_min)} waiting</p>
          ) : null}
        </div>
      </Link>
    </li>
  )
}

export function DiscoverPage() {
  const state = useAsync(() => listRecipes(), [])

  return (
    <div>
      <h1 className="text-4xl font-black tracking-tight [font-stretch:85%] sm:text-5xl">Find something to cook</h1>
      <p className="mt-3 max-w-[60ch] font-serif text-lg text-meta">
        Every recipe in the collection. Search, filters and goal-based ranking come next.
      </p>

      <div className="mt-10">
        {state.status === 'loading' ? <StatusMessage kind="loading" title="Loading recipes…" /> : null}

        {state.status === 'error' ? (
          <StatusMessage kind="error" title="Recipes didn't load">
            {state.message}
          </StatusMessage>
        ) : null}

        {state.status === 'ready' && state.data.items.length === 0 ? (
          <StatusMessage kind="empty" title="No recipes yet">
            Run the seed script on the backend to load the sample recipes.
          </StatusMessage>
        ) : null}

        {state.status === 'ready' && state.data.items.length > 0 ? (
          <>
            <p className="mb-5 text-sm text-meta">{state.data.total} recipes</p>
            <ul>
              {state.data.items.map((recipe) => (
                <RecipeRow key={recipe.id} recipe={recipe} />
              ))}
            </ul>
          </>
        ) : null}
      </div>
    </div>
  )
}
