interface Props {
  title: string
  description: string
}

/** Placeholder page **/
export function PlaceholderPage({ title, description }: Props) {
  return (
    <div>
      <h1 className="text-4xl font-black tracking-tight [font-stretch:85%]">{title}</h1>
      <p className="mt-3 max-w-[60ch] font-serif text-lg text-meta">{description}</p>
    </div>
  )
}
