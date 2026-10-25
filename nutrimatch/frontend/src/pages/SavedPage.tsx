import { Link } from 'react-router'

import { GroceryButton } from '../components/GroceryButton'
import { SaveButton } from '../components/SaveButton'
import { StatusMessage } from '../components/StatusMessage'
import { formatMinutes, titleCase } from '../lib/format'
import { useSavedRecipes } from '../lib/savedRecipes'

export function SavedPage() {
  const recipes = useSavedRecipes()

  return (
    <div>
      <h1 className="text-4xl font-black tracking-tight [font-stretch:85%]">Saved recipes</h1>
      <p className="mt-3 max-w-[60ch] font-serif text-lg text-meta">
        Recipes you save with the (+) button are kept here in this browser.
      </p>

      <div className="mt-10">
        {recipes.length === 0 ? (
          <StatusMessage kind="empty" title="Nothing saved yet">
            Press (+ Save) on any recipe to add it here.{' '}
            <Link to="/" className="text-basil underline">
              Browse recipes
            </Link>
          </StatusMessage>
        ) : (
          <>
            <p className="mb-5 text-sm text-meta">
              {recipes.length} {recipes.length === 1 ? 'recipe' : 'recipes'}
            </p>
            <ul>
              {recipes.map((recipe) => {
                const facts: string[] = []
                if (recipe.cuisine) {
                  facts.push(titleCase(recipe.cuisine))
                }
                if (recipe.meal_type) {
                  facts.push(titleCase(recipe.meal_type))
                }
                facts.push(`Serves ${recipe.servings}`)
                facts.push(formatMinutes(recipe.total_time_min))

                return (
                  <li key={recipe.id} className="flex items-start gap-4 border-b border-line py-5 first:pt-0">
                    <Link to={`/recipes/${recipe.id}`} className="group min-w-0 flex-1">
                      <h2 className="text-xl font-bold leading-snug group-hover:underline">{recipe.title}</h2>
                      {recipe.description ? (
                        <p className="mt-1 max-w-[65ch] font-serif text-[17px] leading-relaxed text-meta">
                          {recipe.description}
                        </p>
                      ) : null}
                      <p className="mt-2 text-sm text-meta">{facts.join(', ')}</p>
                    </Link>
                    <div className="flex shrink-0 flex-col items-end gap-2">
                      <SaveButton recipe={recipe} />
                      <GroceryButton recipe={recipe} />
                    </div>
                  </li>
                )
              })}
            </ul>
          </>
        )}
      </div>
    </div>
  )
}
