interface SkeletonProps {
  label: string
  rows?: number
}

/** Placeholder rows while data loads; the label is what screen readers (and tests) see. */
export default function Skeleton({ label, rows = 3 }: SkeletonProps) {
  return (
    <div className="skeleton" role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton-row" />
      ))}
      <span className="sr-only">{label}</span>
    </div>
  )
}
