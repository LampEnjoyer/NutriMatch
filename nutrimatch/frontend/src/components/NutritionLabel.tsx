import type { Nutrition } from '../api/types'

interface Props {
  servings: number
  nutrition: Nutrition | null
}

function show(value: number | null, unit: string): string {
  if (value === null) {
    return '—'
  }
  return `${Math.round(value)}${unit}`
}

export function NutritionLabel({ servings, nutrition }: Props) {
  const rows = nutrition
    ? [
        { label: 'Calories', value: show(nutrition.calories, ''), indent: false },
        { label: 'Protein', value: show(nutrition.protein_g, ' g'), indent: false },
        { label: 'Carbohydrates', value: show(nutrition.carbohydrates_g, ' g'), indent: false },
        { label: 'Fiber', value: show(nutrition.fiber_g, ' g'), indent: true },
        { label: 'Sugar', value: show(nutrition.sugar_g, ' g'), indent: true },
        { label: 'Total fat', value: show(nutrition.fat_g, ' g'), indent: false },
        { label: 'Saturated fat', value: show(nutrition.saturated_fat_g, ' g'), indent: true },
        { label: 'Sodium', value: show(nutrition.sodium_mg, ' mg'), indent: false },
      ]
    : []

  return (
    <section aria-labelledby="nutrition-heading" className="border-2 border-ink p-3">
      <h2 id="nutrition-heading" className="text-3xl leading-none label-numeral">
        Nutrition facts
      </h2>
      <p className="mt-1 border-b-8 border-ink pb-1 text-sm">
        Per serving · recipe makes {servings}
      </p>

      {nutrition ? (
        <>
          <dl>
            {rows.map((row) => (
              <div
                key={row.label}
                className={`flex items-baseline justify-between border-b border-ink py-1 ${row.indent ? 'pl-4' : ''}`}
              >
                <dt className={row.indent ? '' : 'font-semibold'}>{row.label}</dt>
                <dd className="label-numeral text-lg">{row.value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-2 font-serif text-sm text-meta">
            Estimated from {nutrition.data_source}.
            {nutrition.excluded_ingredients.length > 0
              ? ` Not included: ${nutrition.excluded_ingredients.join(', ')}.`
              : ''}
          </p>
        </>
      ) : (
        <p className="mt-2 font-serif text-sm text-meta">
          Not calculated yet. These will be estimated from the ingredient list using USDA FoodData Central.
        </p>
      )}
    </section>
  )
}
