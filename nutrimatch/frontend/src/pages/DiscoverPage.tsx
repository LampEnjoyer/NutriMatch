import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import { getPreferenceOptions, getPreferences, getRecommendations, savePreferences } from '../api/client'
import type { PreferenceQuestion, PreferencesInput, RecommendationItem, RecommendationList } from '../api/types'
import { PreferencesForm } from '../components/PreferencesForm'
import { SaveButton } from '../components/SaveButton'
import { StatusMessage } from '../components/StatusMessage'
import { formatMinutes, titleCase } from '../lib/format'
import { matchChips, preferenceName } from '../lib/matches'
import { samePreferences, toInput } from '../lib/preferences'
import { useAsync } from '../lib/useAsync'

const PAGE_SIZE = 20
// Unreviewed ingredients are listed up to this many by name on a result; the rest are counted.
const NAMED_UNREVIEWED = 3

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong.'
}

function joinNames(names: string[]): string {
  if (names.length <= 1) {
    return names.join('')
  }
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}

function UnreviewedNote({ names }: { names: string[] }) {
  const shown = names.slice(0, NAMED_UNREVIEWED).map((name) => name.toLowerCase())
  const rest = names.length - shown.length
  const list = rest > 0 ? `${shown.join(', ')} and ${rest} more` : joinNames(shown)
  return <p className="mt-2 text-sm text-tomato">Check labels: allergen information is unverified for {list}.</p>
}

interface RowProps {
  recipe: RecommendationItem
  preferences: PreferencesInput
  showAllergyNote: boolean
}

function RecipeRow({ recipe, preferences, showAllergyNote }: RowProps) {
  const facts: string[] = []
  if (recipe.cuisine) {
    facts.push(titleCase(recipe.cuisine))
  }
  if (recipe.meal_type) {
    facts.push(titleCase(recipe.meal_type))
  }
  facts.push(`Serves ${recipe.servings}`)
  const chips = matchChips(recipe, preferences)

  return (
    <li className="flex items-start gap-4 border-b border-line py-5 first:pt-0">
      <Link
        to={`/recipes/${recipe.id}`}
        className="group grid min-w-0 flex-1 gap-x-8 gap-y-2 sm:grid-cols-[1fr_9rem]"
      >
        <div>
          <h2 className="text-xl font-bold leading-snug group-hover:underline">{recipe.title}</h2>
          {recipe.description ? (
            <p className="mt-1 max-w-[65ch] font-serif text-[17px] leading-relaxed text-meta">{recipe.description}</p>
          ) : null}
          <p className="mt-2 text-sm text-meta">{facts.join(', ')}</p>
          {chips.length > 0 ? (
            <ul aria-label="Why this matches" className="mt-2 flex flex-wrap gap-2">
              {chips.map((chip) => (
                <li key={chip} className="rounded-full bg-basil px-2.5 py-0.5 text-xs font-semibold text-paper">
                  {chip}
                </li>
              ))}
            </ul>
          ) : null}
          {showAllergyNote && recipe.unreviewed_ingredients.length > 0 ? (
            <UnreviewedNote names={recipe.unreviewed_ingredients} />
          ) : null}
        </div>
        <div className="sm:text-right">
          {recipe.total_time_min === null ? (
            <p className="text-sm text-meta">Time not listed</p>
          ) : (
            <p className="label-numeral text-2xl leading-none">{formatMinutes(recipe.total_time_min)}</p>
          )}
          {recipe.inactive_time_min ? (
            <p className="mt-1 text-sm text-tomato">+ {formatMinutes(recipe.inactive_time_min)} waiting</p>
          ) : null}
        </div>
      </Link>
      <SaveButton recipe={recipe} />
    </li>
  )
}

function Notices({ list, preferences, query }: { list: RecommendationList; preferences: PreferencesInput; query: string }) {
  const notices: string[] = []
  if (query) {
    notices.push(`Recipes matching "${query}".`)
  }
  if (list.ranked_by.length > 0) {
    notices.push(`Ranked by ${joinNames(list.ranked_by.map(preferenceName))}.`)
  } else if (list.ignored_preferences.length === 0) {
    notices.push('No preferences chosen, so recipes are listed alphabetically.')
  }
  if (list.ignored_preferences.length > 0) {
    notices.push(
      `Not applied yet: ${joinNames(list.ignored_preferences.map(preferenceName))}. None of the recipes have that information.`,
    )
  }
  if (list.excluded_for_allergies > 0) {
    notices.push(
      `${list.excluded_for_allergies} ${list.excluded_for_allergies === 1 ? 'recipe is' : 'recipes are'} hidden because they contain an allergen you selected.`,
    )
  }
  if (preferences.allergies.length > 0 && list.items.some((item) => item.unreviewed_ingredients.length > 0)) {
    notices.push(
      'Recipes marked "Check labels" use ingredients whose allergen information is unverified. Check those labels yourself before cooking.',
    )
  }

  return (
    <div className="mb-6 space-y-1 text-sm text-meta">
      {notices.map((notice) => (
        <p key={notice}>{notice}</p>
      ))}
    </div>
  )
}

function emptyHint(list: RecommendationList, query: string): string {
  if (list.excluded_for_allergies > 0) {
    return query
      ? 'Every recipe matching your search contains an allergen you selected. Change your allergies or search for something else.'
      : 'Every recipe contains an allergen you selected. Change your allergies to see more.'
  }
  return query ? 'Try a different word, or clear the search to see every recipe.' : 'Run the seed script on the backend to load recipes.'
}

function SearchBar({ applied, onSearch }: { applied: string; onSearch: (query: string) => void }) {
  const [text, setText] = useState(applied)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    onSearch(text.trim())
  }

  function clear() {
    setText('')
    onSearch('')
  }

  return (
    <form role="search" onSubmit={handleSubmit} className="mt-8 flex max-w-xl gap-2">
      <input
        type="search"
        value={text}
        onChange={(event) => setText(event.target.value)}
        maxLength={100}
        placeholder="Search recipes, e.g. salad"
        aria-label="Search recipes"
        className="min-w-0 flex-1 rounded border border-ink px-3 py-2"
      />
      <button type="submit" className="rounded bg-ink px-4 py-2 text-sm font-semibold text-paper hover:bg-meta">
        Search
      </button>
      {applied !== '' ? (
        <button type="button" onClick={clear} className="text-sm text-meta underline hover:text-ink">
          Clear search
        </button>
      ) : null}
    </form>
  )
}

function Results({ preferences, query }: { preferences: PreferencesInput; query: string }) {
  const first = useAsync(() => getRecommendations(PAGE_SIZE, 0, query), [])
  const [more, setMore] = useState<RecommendationItem[]>([])
  const [loadingMore, setLoadingMore] = useState(false)
  const [moreError, setMoreError] = useState<string | null>(null)

  if (first.status === 'loading') {
    return <StatusMessage kind="loading" title="Finding recipes…" />
  }
  if (first.status === 'error') {
    return (
      <StatusMessage kind="error" title="Recommendations didn't load">
        {first.message}
      </StatusMessage>
    )
  }

  const list = first.data
  const items = [...list.items, ...more]

  async function loadMore() {
    setLoadingMore(true)
    setMoreError(null)
    try {
      const next = await getRecommendations(PAGE_SIZE, items.length, query)
      setMore((current) => [...current, ...next.items])
    } catch (error) {
      setMoreError(errorMessage(error))
    } finally {
      setLoadingMore(false)
    }
  }

  if (list.total === 0) {
    return (
      <>
        <Notices list={list} preferences={preferences} query={query} />
        <StatusMessage kind="empty" title={query ? `No recipes match "${query}"` : 'No recipes to show'}>
          {emptyHint(list, query)}
        </StatusMessage>
      </>
    )
  }

  return (
    <>
      <Notices list={list} preferences={preferences} query={query} />
      <p className="mb-5 text-sm text-meta">
        Showing {items.length} of {list.total} recipes
      </p>
      <ul>
        {items.map((recipe) => (
          <RecipeRow
            key={recipe.id}
            recipe={recipe}
            preferences={preferences}
            showAllergyNote={preferences.allergies.length > 0}
          />
        ))}
      </ul>
      {items.length < list.total ? (
        <div className="mt-6">
          <button
            type="button"
            onClick={loadMore}
            disabled={loadingMore}
            className="rounded border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper disabled:opacity-40"
          >
            {loadingMore ? 'Loading…' : 'Show more'}
          </button>
          {moreError ? (
            <p role="alert" className="mt-2 text-sm text-tomato">
              {moreError}
            </p>
          ) : null}
        </div>
      ) : null}
    </>
  )
}

function Discover({ questions, initial }: { questions: PreferenceQuestion[]; initial: PreferencesInput }) {
  const [saved, setSaved] = useState(initial)
  const [draft, setDraft] = useState(initial)
  // The search that is currently applied; the text being typed lives in SearchBar until submitted.
  const [query, setQuery] = useState('')
  // Changing the key remounts Results, which refetches from the first page.
  const [version, setVersion] = useState(0)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  async function apply() {
    setSaving(true)
    setSaveError(null)
    try {
      const result = toInput(await savePreferences(draft))
      setSaved(result)
      setDraft(result)
      setVersion((current) => current + 1)
    } catch (error) {
      setSaveError(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <SearchBar applied={query} onSearch={setQuery} />
      <div className="mt-10 grid gap-10 lg:grid-cols-[18rem_1fr]">
        <aside aria-label="Preferences" className="lg:sticky lg:top-6 lg:self-start">
          <h2 className="mb-4 text-lg font-bold">What are you after?</h2>
          <PreferencesForm
            questions={questions}
            value={draft}
            onChange={setDraft}
            onSubmit={apply}
            dirty={!samePreferences(saved, draft)}
            saving={saving}
            error={saveError}
          />
        </aside>
        <section aria-label="Recommended recipes">
          <Results key={`${version}:${query}`} preferences={saved} query={query} />
        </section>
      </div>
    </>
  )
}

export function DiscoverPage() {
  const setup = useAsync(() => Promise.all([getPreferenceOptions(), getPreferences()]), [])

  return (
    <div>
      <h1 className="text-4xl font-black tracking-tight [font-stretch:85%] sm:text-5xl">Find something to cook</h1>
      <p className="mt-3 max-w-[60ch] font-serif text-lg text-meta">
        Tell us what you are after and the best matches come first. Allergies hide recipes; everything else only
        changes the order.
      </p>

      {setup.status === 'loading' ? (
        <div className="mt-10">
          <StatusMessage kind="loading" title="Loading…" />
        </div>
      ) : null}
      {setup.status === 'error' ? (
        <div className="mt-10">
          <StatusMessage kind="error" title="Couldn't load your preferences">
            {setup.message}
          </StatusMessage>
        </div>
      ) : null}
      {setup.status === 'ready' ? (
        <Discover questions={setup.data[0].questions} initial={toInput(setup.data[1])} />
      ) : null}
    </div>
  )
}
