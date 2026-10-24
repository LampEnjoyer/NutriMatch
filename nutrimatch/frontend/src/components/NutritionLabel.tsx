interface Props {
  servings: number
}

/**
 * Nutrition panel styled after the printed Nutrition Facts label.
 * Phase 1: no values exist yet, so it says so instead of showing placeholder numbers.
 */
export function NutritionLabel({ servings }: Props) {
  const rows = ['Calories', 'Protein', 'Carbohydrates', 'Total fat']

  return (
    <section aria-labelledby="nutrition-heading" className="border-2 border-ink p-3">
      <h2 id="nutrition-heading" className="text-3xl leading-none label-numeral">
        Nutrition facts
      </h2>
      <p className="mt-1 border-b-8 border-ink pb-1 text-sm">
        Per serving · recipe makes {servings}
      </p>
      <dl>
        {rows.map((label) => (
          <div key={label} className="flex items-baseline justify-between border-b border-ink py-1">
            <dt className="font-semibold">{label}</dt>
            <dd className="label-numeral text-lg text-meta">—</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 font-serif text-sm text-meta">
        Not calculated yet. These will be estimated from the ingredient list using USDA FoodData Central.
      </p>
    </section>
  )
}
