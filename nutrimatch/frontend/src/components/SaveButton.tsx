import type { RecipeSummary } from '../api/types'
import { toggleSaved, useSavedRecipes } from '../lib/savedRecipes'

interface Props {
  recipe: RecipeSummary
}

/** "+ Save" adds the recipe to the Saved list; pressing it again removes it. */
export function SaveButton({ recipe }: Props) {
  const saved = useSavedRecipes().some((item) => item.id === recipe.id)

  return (
    <button
      type="button"
      onClick={() => toggleSaved(recipe)}
      aria-pressed={saved}
      aria-label={saved ? `Remove ${recipe.title} from saved recipes` : `Save ${recipe.title}`}
      title={saved ? 'Remove from saved' : 'Save recipe'}
      className={
        saved
          ? 'inline-flex shrink-0 items-center gap-1 rounded-full border border-basil bg-basil px-3 py-1 text-sm font-semibold text-paper hover:border-basil-dark hover:bg-basil-dark'
          : 'inline-flex shrink-0 items-center gap-1 rounded-full border border-ink px-3 py-1 text-sm font-semibold hover:bg-ink hover:text-paper'
      }
    >
      <span aria-hidden="true" className="text-base leading-none">
        {saved ? '✓' : '+'}
      </span>
      {saved ? 'Saved' : 'Save'}
    </button>
  )
}
