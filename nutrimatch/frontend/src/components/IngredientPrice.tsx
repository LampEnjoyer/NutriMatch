import type { LineCost } from '../api/types'
import { formatMoney } from '../lib/format'

interface Props {
  line: LineCost
}

function ProductLink({ line }: Props) {
  const product = line.product
  if (product === null) {
    return null
  }
  let label = product.description
  if (product.size_text) {
    label = `${label}, ${product.size_text}`
  }
  if (product.product_url) {
    return (
      <a href={product.product_url} target="_blank" rel="noreferrer" className="underline decoration-line underline-offset-2 hover:decoration-ink">
        {label}
      </a>
    )
  }
  return <span>{label}</span>
}

/** One line under an ingredient: which product, its price, and what the recipe uses. */
export function IngredientPrice({ line }: Props) {
  const product = line.product

  if (line.status === 'not_purchased' || line.status === 'unmeasured' || line.status === 'no_match') {
    return <p className="mt-1 text-sm text-meta">{line.reason}</p>
  }

  if (product === null) {
    return null
  }

  return (
    <div className="mt-1 text-sm text-meta">
      <p>
        <span className="font-semibold text-ink tabular-nums">{formatMoney(product.package_price)}</span>{' '}
        <ProductLink line={line} />
        {product.on_sale && product.regular_price !== null ? (
          <span className="text-basil"> on sale, usually {formatMoney(product.regular_price)}</span>
        ) : null}
      </p>

      {line.status === 'priced' && line.used_cost !== null ? (
        <p>
          This recipe uses about <span className="tabular-nums">{formatMoney(line.used_cost)}</span> of it
          {line.packages !== null && line.packages > 1 ? `; buy ${line.packages}` : ''}.
          {line.is_pantry_staple ? ' You probably have this already.' : ''}
        </p>
      ) : null}

      {line.status === 'needs_conversion' ? (
        <p className="text-tomato">
          {line.is_pantry_staple ? 'You probably have this already. ' : ''}
          Can't tell how much of this package the recipe uses yet.
        </p>
      ) : null}

      {product.sold_by_weight ? <p>Sold by weight, so the price at the register may differ.</p> : null}
    </div>
  )
}
