import { Link, useParams } from 'react-router'

import { ApiError, getRecipe } from '../api/client'
import type { LineCost, RecipeDetail } from '../api/types'
import { CostPanel } from '../components/CostPanel'
import { GroceryButton } from '../components/GroceryButton'
import { IngredientPrice } from '../components/IngredientPrice'
import { NutritionLabel } from '../components/NutritionLabel'
import { SaveButton } from '../components/SaveButton'
import { StatusMessage } from '../components/StatusMessage'
import { formatAmount, formatMinutes, titleCase } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import { useRecipePricing } from '../lib/useRecipePricing'

function TimeFacts({ recipe }: { recipe: RecipeDetail }) {
  const items: { label: string; value: string }[] = [
    { label: 'Prep', value: formatMinutes(recipe.preparation_time_min) },
    { label: 'Cook', value: formatMinutes(recipe.cooking_time_min) },
    { label: 'Total', value: formatMinutes(recipe.total_time_min) },
  ]
  if (recipe.inactive_time_min) {
    items.push({ label: 'Waiting', value: formatMinutes(recipe.inactive_time_min) })
  }
  items.push({ label: 'Serves', value: String(recipe.servings) })

  return (
    <dl className="mt-6 flex flex-wrap gap-x-8 gap-y-3">
      {items.map((item) => (
        <div key={item.label}>
          <dt className="text-sm text-meta">{item.label}</dt>
          <dd className="label-numeral text-2xl leading-tight">{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

/** Shown when we can't vouch for this recipe's allergen information, so the user checks for themselves. */
function AllergenNotice({ recipe }: { recipe: RecipeDetail }) {
  const names = recipe.unreviewed_ingredients.map((name) => name.toLowerCase())
  return (
    <div role="note" className="mt-6 max-w-prose border-l-4 border-tomato py-2 pl-4">
      <p className="font-semibold text-tomato">Check ingredient labels if you have an allergy</p>
      <p className="mt-1 font-serif text-meta">
        {names.length > 0
          ? `Allergen information is unverified for: ${names.join(', ')}. Brands vary, so read the packaging.`
          : 'Some ingredient lines could not be fully read, so the allergen information may be incomplete.'}
      </p>
    </div>
  )
}

function RecipeView({ recipe }: { recipe: RecipeDetail }) {
  const pricing = useRecipePricing(recipe.id)

  // Index price lines by ingredient position so each one renders under its own ingredient.
  const priceByPosition = new Map<number, LineCost>()
  if (pricing.state.status === 'ready' && pricing.state.data.cost !== null) {
    for (const line of pricing.state.data.cost.lines) {
      priceByPosition.set(line.position, line)
    }
  }

  const facts: string[] = []
  if (recipe.cuisine) {
    facts.push(titleCase(recipe.cuisine))
  }
  if (recipe.meal_type) {
    facts.push(titleCase(recipe.meal_type))
  }

  return (
    <article>
      <Link to="/" className="text-sm text-meta hover:text-ink">
        Back to recipes
      </Link>
      <h1 className="mt-4 max-w-[22ch] text-4xl font-black leading-[1.05] tracking-tight [font-stretch:85%] sm:text-5xl">
        {recipe.title}
      </h1>
      {facts.length > 0 ? <p className="mt-3 text-meta">{facts.join(', ')}</p> : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <SaveButton recipe={recipe} />
        <GroceryButton recipe={recipe} />
      </div>
      {recipe.description ? (
        <p className="mt-4 max-w-[60ch] font-serif text-lg leading-relaxed">{recipe.description}</p>
      ) : null}
      <TimeFacts recipe={recipe} />
      {recipe.allergy_info_complete ? null : <AllergenNotice recipe={recipe} />}

      <div className="mt-10 grid gap-10 lg:grid-cols-[1fr_20rem]">
        <div className="grid gap-10 md:grid-cols-[18rem_1fr]">
          <section aria-labelledby="ingredients-heading">
            <h2 id="ingredients-heading" className="border-b-2 border-ink pb-1 text-lg font-bold">
              Ingredients
            </h2>
            <ul className="mt-2">
              {recipe.ingredients.map((line, index) => {
                const price = priceByPosition.get(index)
                return (
                  <li key={`${line.ingredient_id}-${index}`} className="border-b border-line py-2">
                    <span className="font-semibold tabular-nums">{formatAmount(line.quantity, line.unit)}</span>{' '}
                    <span>{line.name}</span>
                    {line.preparation_notes ? <span className="text-meta">, {line.preparation_notes}</span> : null}
                    {line.is_optional ? <span className="text-meta"> (optional)</span> : null}
                    {line.allergens_reviewed ? null : <span className="text-sm text-tomato"> (allergens unverified)</span>}
                    {price ? <IngredientPrice line={price} /> : null}
                  </li>
                )
              })}
            </ul>
          </section>

          <section aria-labelledby="method-heading">
            <h2 id="method-heading" className="border-b-2 border-ink pb-1 text-lg font-bold">
              Method
            </h2>
            <ol className="mt-3 space-y-4">
              {recipe.instructions.map((step, index) => (
                <li key={index} className="grid grid-cols-[2rem_1fr]">
                  <span className="label-numeral text-xl leading-7">{index + 1}</span>
                  <p className="max-w-[62ch] font-serif text-[17px] leading-7">{step}</p>
                </li>
              ))}
            </ol>
          </section>
        </div>

        <aside className="lg:sticky lg:top-6 lg:self-start">
          <NutritionLabel servings={recipe.servings} />
          <CostPanel pricing={pricing} />
          <p className="mt-4 text-sm text-meta">Source: {recipe.source_name}</p>
        </aside>
      </div>
    </article>
  )
}

export function RecipePage() {
  const params = useParams()
  const recipeId = Number(params.recipeId)
  const isValidId = Number.isInteger(recipeId) && recipeId > 0

  const state = useAsync(() => {
    if (!isValidId) {
      return Promise.reject(new ApiError(404, 'That recipe link is invalid.'))
    }
    return getRecipe(recipeId)
  }, [recipeId])

  if (state.status === 'loading') {
    return <StatusMessage kind="loading" title="Loading recipe…" />
  }
  if (state.status === 'error') {
    return (
      <StatusMessage kind="error" title="Recipe unavailable">
        {state.message}{' '}
        <Link to="/" className="text-basil underline">
          Browse all recipes
        </Link>
      </StatusMessage>
    )
  }
  return <RecipeView recipe={state.data} />
}
