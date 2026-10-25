import type { FormEvent } from 'react'

import type { PreferenceOption, PreferenceQuestion, PreferencesInput } from '../api/types'
import {
  EMPTY_PREFERENCES,
  NO_PREFERENCE,
  multiAnswer,
  offersNoPreference,
  singleAnswer,
  withSingleAnswer,
  withToggledAnswer,
} from '../lib/preferences'

interface Props {
  questions: PreferenceQuestion[]
  value: PreferencesInput
  onChange: (next: PreferencesInput) => void
  onSubmit: () => void
  dirty: boolean
  saving: boolean
  error: string | null
}

interface ChoiceProps {
  type: 'radio' | 'checkbox'
  name: string
  option: PreferenceOption
  checked: boolean
  onChange: () => void
}

function Choice({ type, name, option, checked, onChange }: ChoiceProps) {
  return (
    <label className="cursor-pointer">
      <input type={type} name={name} checked={checked} onChange={onChange} className="peer sr-only" />
      <span className="block rounded-full border border-line px-3 py-1 text-sm hover:border-ink peer-checked:border-ink peer-checked:bg-ink peer-checked:text-paper peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-basil">
        {option.label}
      </span>
    </label>
  )
}

function Question({
  question,
  value,
  onChange,
}: {
  question: PreferenceQuestion
  value: PreferencesInput
  onChange: (next: PreferencesInput) => void
}) {
  let choices
  if (question.type === 'multi') {
    const selected = multiAnswer(value, question)
    choices = question.options.map((option) => (
      <Choice
        key={option.value}
        type="checkbox"
        name={question.id}
        option={option}
        checked={selected.includes(option.value)}
        onChange={() => onChange(withToggledAnswer(value, question, option.value))}
      />
    ))
  } else {
    const answer = singleAnswer(value, question)
    // A question with no explicit "don't care" gets a clear choice so an answer can be undone.
    const options = offersNoPreference(question)
      ? question.options
      : [...question.options, { value: NO_PREFERENCE, label: 'No preference' }]
    choices = options.map((option) => {
      const checked = option.value === NO_PREFERENCE ? answer === null || answer === NO_PREFERENCE : answer === option.value
      return (
        <Choice
          key={option.value}
          type="radio"
          name={question.id}
          option={option}
          checked={checked}
          onChange={() => onChange(withSingleAnswer(value, question, option.value === NO_PREFERENCE ? null : option.value))}
        />
      )
    })
  }

  return (
    <fieldset className="border-t border-line pt-4">
      <legend className="float-left mb-2 w-full text-sm font-bold">{question.label}</legend>
      <div className="clear-both flex flex-wrap gap-2">{choices}</div>
      {question.type === 'multi' && question.field === 'meal_types' ? (
        <p className="mt-2 text-xs text-meta">Leave empty for any meal.</p>
      ) : null}
      {question.help ? <p className="mt-2 text-xs leading-relaxed text-meta">{question.help}</p> : null}
    </fieldset>
  )
}

export function PreferencesForm({ questions, value, onChange, onSubmit, dirty, saving, error }: Props) {
  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    onSubmit()
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Your preferences" className="space-y-4">
      {questions.map((question) => (
        <Question key={question.id} question={question} value={value} onChange={onChange} />
      ))}

      {/* Stays in view at the bottom of the panel while the questions scroll. */}
      <div className="sticky bottom-0 flex flex-wrap items-center gap-3 border-t border-line bg-paper py-4">
        <button
          type="submit"
          disabled={!dirty || saving}
          className="rounded bg-basil px-4 py-2 text-sm font-semibold text-paper hover:bg-basil-dark disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving ? 'Updating…' : 'Update recommendations'}
        </button>
        <button
          type="button"
          onClick={() => onChange(EMPTY_PREFERENCES)}
          className="text-sm text-meta underline hover:text-ink"
        >
          Clear all
        </button>
      </div>
      {error ? (
        <p role="alert" className="text-sm text-tomato">
          {error}
        </p>
      ) : null}
    </form>
  )
}
