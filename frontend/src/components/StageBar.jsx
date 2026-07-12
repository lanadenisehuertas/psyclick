const STAGES = ['PHQ-9', 'GAD-7', 'Emotional Response', 'Final Stage']

export default function StageBar({ active }) {
  return (
    <div className="mb-6">
      <div className="flex justify-between mb-2">
        {STAGES.map((s, i) => (
          <span key={s} className={`text-xs font-medium ${i === active ? 'text-accent' : 'text-tsub'}`}>
            {s}
          </span>
        ))}
      </div>
      <div className="h-2 bg-border rounded-full overflow-hidden">
        <div
          className="h-full bg-accent rounded-full transition-all duration-500"
          style={{ width: `${(active / 3) * 100}%` }}
        />
      </div>
    </div>
  )
}
