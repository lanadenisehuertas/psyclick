// active: 0 = PHQ-9, 1 = GAD-7, 2 = Emotional Response, 3 = Report (completion)
const STAGES = ['PHQ-9', 'GAD-7', 'Emotional Response', 'Report']

export default function StageBar({ active }) {
  // Progress starts at 25% on the first step and reaches 100% at the last
  const pct = Math.round(((active + 1) / STAGES.length) * 100)

  return (
    <div className="mb-6">
      <div className="flex justify-between mb-2">
        {STAGES.map((s, i) => (
          <span
            key={s}
            className={`text-xs font-medium ${
              i < active
                ? 'text-success'
                : i === active
                  ? 'text-accent font-semibold'
                  : 'text-tsub'
            }`}
          >
            {i < active ? '✓ ' : ''}{s}
          </span>
        ))}
      </div>
      <div className="h-2 bg-border rounded-full overflow-hidden">
        <div
          className="h-full bg-accent rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
