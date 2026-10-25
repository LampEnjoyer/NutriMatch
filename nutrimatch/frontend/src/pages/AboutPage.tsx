const SOURCES = [
  'https://ers.usda.gov/data-products/charts-of-note/114212?cpid=email',
  'https://www.ispor.org/heor-resources/presentations-database/presentation/intl2020-3182/101657',
  'https://www.aicr.org/resources/blog/where-you-eat-matters-for-your-health-sort-of/',
  'https://publichealth.jhu.edu/2024/ultraprocessed-foods-account-for-more-than-half-of-calories-consumed-at-home',
]

function Cite({ n }: { n: number }) {
  return (
    <sup>
      <a href={`#source-${n}`} className="font-semibold text-basil hover:underline">
        [{n}]
      </a>
    </sup>
  )
}

export function AboutPage() {
  return (
    <div>
      <h1 className="text-4xl font-black tracking-tight [font-stretch:85%] sm:text-5xl">About</h1>

      <div className="mt-3 max-w-[75ch] space-y-5 font-serif text-lg leading-relaxed">
        <p className="text-meta">Home cooking is, for many reasons, better than eating out. Here are some facts:</p>
        <p>
          More than half of US national food spending is spent on eating out
          <Cite n={1} />. On average, you can save over $160 a month by eating out less
          <Cite n={2} />.
        </p>
        <p>
          Eating out can increase your calorie intake by an average of 200 calories a day as well as your intake of
          fat, sodium, cholesterol. This is especially true for fast foods
          <Cite n={3} />.
        </p>
        <p>
          However, this only matters if you choose the right foods to cook - nearly half of all calories the average
          American eats at home consists of ultra processed foods
          <Cite n={4} />.
        </p>
        <p>
          This is where we hope NutriMatch can help by choosing the right recipes and understanding where you can
          source your ingredients.
        </p>
      </div>

      <section aria-labelledby="sources-heading" className="mt-10 max-w-[60ch] border-t border-line pt-6">
        <h2 id="sources-heading" className="text-xl font-bold">
          Sources
        </h2>
        <ol className="mt-3 space-y-2 text-sm">
          {SOURCES.map((url, i) => (
            <li key={url} id={`source-${i + 1}`} className="flex gap-2">
              <span className="text-meta">[{i + 1}]</span>
              <a href={url} target="_blank" rel="noreferrer" className="break-all text-basil underline">
                {url}
              </a>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}
