import { ScaleBar } from '../components/ReportParts.jsx'

// ── Population comparison (specialist detail) ───────────────────────────────
const NORM_LABELS = {
  t2_score:  { name: 'Overall behaviour change', tech: 'Hotelling T²' },
  psi:       { name: 'Slowing',                  tech: 'Psychomotor Slowing Index (PSI)' },
  pai:       { name: 'Restlessness',             tech: 'Psychomotor Agitation Index (PAI)' },
  phq_score: { name: 'Depression questionnaire', tech: 'PHQ-9' },
  gad_score: { name: 'Anxiety questionnaire',    tech: 'GAD-7' },
}

export function percentileValue(pct) {
  return pct >= 99.5 ? '99+' : String(Math.round(pct))
}

export function percentileText(pct) {
  if (pct === undefined || pct === null) return ''
  if (pct >= 99.5) return 'Higher than almost all healthy adults'
  if (pct < 1) return 'Lower than almost all healthy adults'
  if (pct < 85) return `Typical — higher than ${Math.round(pct)}% of healthy adults`
  return `Higher than ${Math.round(pct)}% of healthy adults`
}

export function NormativeComparison({ metrics, loading }) {
  const hasData = metrics && Object.keys(metrics).length > 0
  const keys = ['t2_score', 'psi', 'pai', 'phq_score', 'gad_score'].filter(k => hasData && metrics[k])
  const n = hasData ? metrics[keys[0]]?.count : null

  if (loading) {
    return (
      <div className="py-8 text-center" role="status">
        <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        <p className="text-tsub text-sm">Loading comparison…</p>
      </div>
    )
  }
  if (!hasData) {
    return (
      <div className="rounded-xl border border-border bg-[#F7FAFA] px-5 py-6 text-center">
        <p className="font-semibold text-tmain mb-1">Comparison not available for this session</p>
        <p className="text-sm text-tsub">The session must be saved before it can be compared with the healthy reference group.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-tsub leading-relaxed max-w-[90ch]">
        Each score is ranked against {n ?? 'the'} healthy adults (one session each, PHQ-9 and GAD-7 below 10).
        The marker shows where this client sits; the green zone is where most healthy adults fall.
      </p>
      <div className="divide-y divide-border">
        {keys.map(k => {
          const m = metrics[k]
          const pct = Math.max(0, Math.min(100, Number(m.pct)))
          const tone = pct >= 95 ? 'text-coral-ink' : pct >= 85 ? 'text-amber-ink' : 'text-success-ink'
          return (
            <div key={k} className="py-4 grid grid-cols-12 gap-4 items-center">
              <div className="col-span-12 md:col-span-4">
                <p className="font-semibold text-tmain">{NORM_LABELS[k].name}</p>
                <p className="text-xs text-tsub">{NORM_LABELS[k].tech}</p>
              </div>
              <div className="col-span-12 md:col-span-5">
                <ScaleBar
                  value={pct}
                  zones={[{ to: 85, label: 'Typical', tone: 'good' }, { to: 95, label: 'Higher', tone: 'warn' }, { to: 100, label: 'Top 5%', tone: 'high' }]}
                  markerLabel={percentileValue(pct)}
                  ariaLabel={`${NORM_LABELS[k].name}: ${percentileText(pct)}`}
                />
              </div>
              <div className="col-span-12 md:col-span-3 text-sm">
                <p className={`font-semibold ${tone}`}>{percentileText(pct)}</p>
                <p className="text-tsub tabular-nums mt-0.5">
                  Client {Number(m.patient).toFixed(1)} · healthy avg {Number(m.norm_mean).toFixed(1)} · z {m.z > 0 ? '+' : ''}{Number(m.z).toFixed(2)}
                </p>
              </div>
            </div>
          )
        })}
      </div>
      <p className="text-xs text-tsub border-t border-border pt-3">
        The overall result compares the client with their own calibration (within-session baseline). This table adds the
        comparison with other people, so both views can be read together (Thesis §1.3).
      </p>
    </div>
  )
}

// ── Question-by-question breakdown (specialist detail) ──────────────────────
const ITEM_FLAG = {
  GREEN:   { label: 'Typical',    cls: 'bg-success/15 text-success-ink' },
  AMBER:   { label: 'Elevated',   cls: 'bg-amber/15 text-amber-ink' },
  RED:     { label: 'High',       cls: 'bg-coral/15 text-coral-ink' },
  NO_DATA: { label: 'Not scored', cls: 'bg-border/60 text-tsub' },
}

export function QuestionBreakdown({ snapshots, itemP95 }) {
  const flagged   = snapshots.filter(s => s.flag === 'RED' || s.flag === 'AMBER')
  const redItems  = snapshots.filter(s => s.flag === 'RED').map(s => s.item_id).join(', ')
  const ambItems  = snapshots.filter(s => s.flag === 'AMBER').map(s => s.item_id).join(', ')
  const maxT2Snap = snapshots.reduce((best, s) => (s.t2_score || 0) > (best.t2_score || 0) ? s : best, snapshots[0])
  const maxPauseSnap = snapshots.reduce((best, s) => (s.pre_typing_pause_ms || 0) > (best.pre_typing_pause_ms || 0) ? s : best, snapshots[0])
  const allHovers = snapshots.flatMap(s => s.hover_words || [])
  const topWord   = [...allHovers].sort((a, b) => (b.dwell_ms || 0) - (a.dwell_ms || 0))[0]?.word

  return (
    <div>
      <div className="grid sm:grid-cols-3 gap-4 text-sm mb-5">
        <div className="rounded-xl bg-[#F7FAFA] p-4">
          <p className="text-xs font-semibold text-tsub uppercase tracking-wide mb-1">Prompts above typical</p>
          {flagged.length === 0 ? (
            <p className="text-success-ink font-semibold">None — all prompts typical</p>
          ) : (
            <>
              <p className="font-semibold text-tmain">{flagged.length} of {snapshots.length} prompts</p>
              {redItems && <p className="text-coral-ink mt-0.5">High: {redItems}</p>}
              {ambItems && <p className="text-amber-ink">Elevated: {ambItems}</p>}
            </>
          )}
        </div>
        <div className="rounded-xl bg-[#F7FAFA] p-4">
          <p className="text-xs font-semibold text-tsub uppercase tracking-wide mb-1">Largest change</p>
          <p className="font-semibold text-tmain">Prompt {maxT2Snap?.item_id || '—'} <span className="font-normal text-tsub">(T² {Number(maxT2Snap?.t2_score || 0).toFixed(1)})</span></p>
          <p className="text-tsub mt-0.5">{maxT2Snap?.group_name?.split(':')[1]?.trim() || '—'}, level {maxT2Snap?.level || '—'}</p>
        </div>
        <div className="rounded-xl bg-[#F7FAFA] p-4">
          <p className="text-xs font-semibold text-tsub uppercase tracking-wide mb-1">Longest pause before typing</p>
          <p className="font-semibold text-tmain">Prompt {maxPauseSnap?.item_id || '—'} <span className="font-normal text-tsub">({(Math.round(maxPauseSnap?.pre_typing_pause_ms || 0) / 1000).toFixed(1)} s)</span></p>
          {topWord && <p className="text-tsub mt-0.5">Word read longest: <span className="font-semibold text-tmain">&ldquo;{topWord}&rdquo;</span></p>}
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="w-full text-[13px]">
          <caption className="sr-only">Biometric results for each prompt</caption>
          <thead>
            <tr className="bg-[#F7FAFA] text-tsub text-xs font-semibold uppercase tracking-wide">
              {['Prompt', 'Topic', 'Level', 'Change (T²)', 'PSI', 'PAI', 'Key gap', 'Pause', 'Word read longest', 'Result', 'What it suggests'].map(h => (
                <th key={h} scope="col" className="px-2.5 py-3 text-left whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {snapshots.map((snap, i) => {
              const lv     = snap.level || 'A'
              const noData = snap.flag === 'NO_DATA'
              const f      = ITEM_FLAG[snap.flag] || ITEM_FLAG.GREEN
              const psi_v  = Number(snap.psi || 0)
              const pai_v  = Number(snap.pai || 0)
              const t2v    = Number(snap.t2_score || 0)
              const topHW  = (snap.hover_words || [])[0]
              let interp
              if (snap.flag === 'RED') {
                interp = psi_v > pai_v * 1.2 ? 'Marked slowing on this prompt'
                  : pai_v > psi_v * 1.2 ? 'Marked restlessness on this prompt'
                  : 'Marked change — slowing and restlessness'
              } else if (snap.flag === 'AMBER') {
                interp = `Some change on a ${lv === 'C' ? 'strong' : lv === 'B' ? 'moderate' : 'mild'} prompt`
              } else if (noData) {
                interp = 'No typing captured'
              } else {
                interp = 'Typical'
              }
              return (
                <tr key={i} className={`border-t border-border/60 ${i % 2 === 1 ? 'bg-[#FAFCFC]' : 'bg-white'}`}>
                  <td className="px-2.5 py-2.5 font-bold text-tmain">{snap.item_id || '—'}</td>
                  <td className="px-2.5 py-2.5 text-tsub max-w-[120px] truncate" title={snap.group_name || ''}>{snap.group_name?.split(':')[1]?.trim() || '—'}</td>
                  <td className="px-2.5 py-2.5 font-semibold text-tmain">{lv}</td>
                  <td className={`px-2.5 py-2.5 tabular-nums ${!noData && itemP95 && t2v > itemP95 ? 'text-coral-ink font-semibold' : 'text-tmain'}`}>{noData ? '—' : t2v.toFixed(1)}</td>
                  <td className="px-2.5 py-2.5 tabular-nums text-tsub">{noData ? '—' : psi_v.toFixed(1)}</td>
                  <td className="px-2.5 py-2.5 tabular-nums text-tsub">{noData ? '—' : pai_v.toFixed(1)}</td>
                  <td className="px-2.5 py-2.5 tabular-nums text-tsub whitespace-nowrap">{noData ? '—' : `${Math.round((snap.flight_time || 0) * 1000)} ms`}</td>
                  <td className="px-2.5 py-2.5 tabular-nums text-tsub whitespace-nowrap">{(Math.round(snap.pre_typing_pause_ms || 0) / 1000).toFixed(1)} s</td>
                  <td className="px-2.5 py-2.5 text-tmain max-w-[120px] truncate">
                    {topHW ? <span className="font-medium">&ldquo;{topHW.word}&rdquo;</span> : <span className="text-tsub">—</span>}
                  </td>
                  <td className="px-2.5 py-2.5">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${f.cls}`}>{f.label}</span>
                  </td>
                  <td className="px-2.5 py-2.5 text-tsub min-w-[150px]">{interp}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {itemP95 && (
        <p className="text-xs text-tsub mt-3">
          A single prompt counts as above typical when its change is higher than in 95% of healthy adults (T² &gt; {itemP95.toFixed(0)}).
        </p>
      )}
    </div>
  )
}

