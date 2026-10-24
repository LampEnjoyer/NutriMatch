import type { RecipeSummary } from '../api/types'
import { toggleGroceryRecipe, useGroceryList } from '../lib/groceryList'

interface Props {
  recipe: RecipeSummary
}

/** Adds the recipe's ingredients to the grocery list; pressing it again takes them off. */
export function GroceryButton({ recipe }: Props) {
  const added = useGroceryList().recipes.some((item) => item.id === recipe.id)

  return (
    <button
      type="button"
      onClick={() => toggleGroceryRecipe(recipe)}
      aria-pressed={added}
      aria-label={added ? `Remove ${recipe.title} from grocery list` : `Add ${recipe.title} to grocery list`}
      className={
        added
          ? 'inline-flex shrink-0 items-center gap-1 rounded-full border border-basil bg-basil px-3 py-1 text-sm font-semibold text-paper hover:border-basil-dark hover:bg-basil-dark'
          : 'inline-flex shrink-0 items-center gap-1 rounded-full border border-ink px-3 py-1 text-sm font-semibold hover:bg-ink hover:text-paper'
      }
    >
      <span aria-hidden="true" className="text-base leading-none">
        {added ? '✓' : '+'}
      </span>
      {added ? 'On grocery list' : 'Grocery list'}
    </button>
  )
}
