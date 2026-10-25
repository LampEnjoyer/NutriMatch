import { Link } from 'react-router'

import { getRecipe } from '../api/client'
import { GroceryButton } from '../components/GroceryButton'
import { StatusMessage } from '../components/StatusMessage'
import {
  clearGroceryList,
  combineIngredients,
  toggleChecked,
  toggleGroceryRecipe,
  uncheckAll,
  useGroceryList,
  type GroceryItem,
  type GroceryRecipe,
} from '../lib/groceryList'
import { useSavedRecipes } from '../lib/savedRecipes'
import { useAsync } from '../lib/useAsync'

function ItemRow({ item, checked }: { item: GroceryItem; checked: boolean }) {
  const amount = item.toTaste ? 'To taste' : item.amounts.join(' + ')
  return (
    <li className="border-b border-line">
      <label className="flex cursor-pointer items-start gap-3 py-3">
        <input
          type="checkbox"
          checked={checked}
          onChange={() => toggleChecked(item.key)}
          className="mt-1 size-4 shrink-0 accent-basil"
        />
        <span className={checked ? 'text-meta line-through' : ''}>
          <span className="font-semibold tabular-nums">{amount}</span> {item.name}
          {item.optional ? <span className="text-meta"> (optional)</span> : null}
          <span className="block text-sm text-meta">For {item.recipes.join(', ')}</span>
        </span>
      </label>
    </li>
  )
}

function Checklist({ recipes, checked }: { recipes: GroceryRecipe[]; checked: string[] }) {
  const ids = recipes.map((recipe) => recipe.id)
  const details = useAsync(() => Promise.all(ids.map((id) => getRecipe(id))), [ids.join(',')])

  if (details.status === 'loading') {
    return <StatusMessage kind="loading" title="Building your list…" />
  }
  if (details.status === 'error') {
    return (
      <StatusMessage kind="error" title="Couldn't load the ingredients">
        {details.message}
      </StatusMessage>
    )
  }

  const items = combineIngredients(details.data)
  const checkedSet = new Set(checked)
  // Items stay in place when ticked, so the list doesn't jump around while shopping.
  const done = items.filter((item) => checkedSet.has(item.key))

  return (
    <>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2 border-b-2 border-ink pb-1">
        <h2 className="text-lg font-bold">Ingredients</h2>
        <p className="text-sm text-meta">
          {done.length} of {items.length}
        </p>
      </div>
      <ul>
        {items.map((item) => (
          <ItemRow key={item.key} item={item} checked={checkedSet.has(item.key)} />
        ))}
      </ul>
      <p className="mt-3 text-sm text-meta">
        Amounts in the same unit are added up, and amounts in different units are listed separately.
      </p>
      {done.length > 0 ? (
        <button type="button" onClick={uncheckAll} className="mt-4 text-sm text-meta underline hover:text-ink">
          Untick everything
        </button>
      ) : null}
    </>
  )
}

export function GroceryPage() {
  const { recipes, checked } = useGroceryList()
  const saved = useSavedRecipes()
  const savedNotOnList = saved.filter((recipe) => !recipes.some((item) => item.id === recipe.id))

  return (
    <div>
      <h1 className="text-4xl font-black tracking-tight [font-stretch:85%]">Grocery list</h1>
      <p className="mt-3 max-w-[60ch] font-serif text-lg text-meta">
        Pick recipes and their ingredients are combined into one checklist.
      </p>

      <div className="mt-10 grid gap-10 lg:grid-cols-[18rem_1fr]">
        <aside aria-label="Recipes on the list" className="lg:sticky lg:top-6 lg:self-start">
          <h2 className="border-b-2 border-ink pb-1 text-lg font-bold">Recipes</h2>
          {recipes.length === 0 ? (
            <p className="mt-3 text-sm text-meta">No recipes yet.</p>
          ) : (
            <ul>
              {recipes.map((recipe) => (
                <li key={recipe.id} className="flex items-start justify-between gap-3 border-b border-line py-2">
                  <Link to={`/recipes/${recipe.id}`} className="hover:underline">
                    {recipe.title}
                  </Link>
                  <button
                    type="button"
                    onClick={() => toggleGroceryRecipe(recipe)}
                    aria-label={`Remove ${recipe.title} from grocery list`}
                    className="shrink-0 text-sm text-meta underline hover:text-tomato"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}

          {savedNotOnList.length > 0 ? (
            <>
              <h2 className="mt-8 border-b-2 border-ink pb-1 text-lg font-bold">Add from saved</h2>
              <ul>
                {savedNotOnList.map((recipe) => (
                  <li key={recipe.id} className="flex items-start justify-between gap-3 border-b border-line py-2">
                    <span>{recipe.title}</span>
                    <GroceryButton recipe={recipe} />
                  </li>
                ))}
              </ul>
            </>
          ) : null}

          {recipes.length > 0 ? (
            <button
              type="button"
              onClick={clearGroceryList}
              className="mt-6 text-sm text-meta underline hover:text-tomato"
            >
              Clear grocery list
            </button>
          ) : null}
        </aside>

        <section aria-label="Shopping checklist">
          {recipes.length === 0 ? (
            <StatusMessage kind="empty" title="Your grocery list is empty">
              Press (+ Grocery list) on a recipe, or add one of your saved recipes.{' '}
              <Link to="/" className="text-basil underline">
                Browse recipes
              </Link>
            </StatusMessage>
          ) : (
            <Checklist recipes={recipes} checked={checked} />
          )}
        </section>
      </div>
    </div>
  )
}
