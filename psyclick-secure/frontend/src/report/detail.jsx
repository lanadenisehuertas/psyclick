import { ScaleBar } from '../components/ReportParts.jsx'
import { topicAverages } from './visuals.jsx'
import { DOMAIN_NAMES } from './text.js'

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
export function QuestionBreakdown({ snapshots, itemP95 }) {
  // Healthy limits describe topic averages; a single prompt is compared with
  // the client's own other prompts instead.
  const topics    = topicAverages(snapshots)
  const above     = topics.filter(t => itemP95 && t.avg > itemP95)
  const scoredT2  = snapshots.filter(s => s.flag !== 'NO_DATA').map(s => Number(s.t2_score || 0)).sort((a, b) => a - b)
  const ownMedian = scoredT2.length ? scoredT2[Math.floor(scoredT2.length / 2)] : 0
  const maxT2Snap = snapshots.reduce((best, s) => (s.t2_score || 0) > (best.t2_score || 0) ? s : best, snapshots[0])
  const maxPauseSnap = snapshots.reduce((best, s) => (s.pre_typing_pause_ms || 0) > (best.pre_typing_pause_ms || 0) ? s : best, snapshots[0])
  const allHovers = snapshots.flatMap(s => s.hover_words || [])
  const topWord   = [...allHovers].sort((a, b) => (b.dwell_ms || 0) - (a.dwell_ms || 0))[0]?.word

  return (
    <div>
      <div className="grid sm:grid-cols-3 gap-4 text-sm mb-5">
        <div className="rounded-xl bg-[#F7FAFA] p-4">
          <p className="text-xs font-semibold text-tsub uppercase tracking-wide mb-1">Topics above healthy adults</p>
          {above.length === 0 ? (
            <p className="text-success-ink font-semibold">None — every topic average in the healthy range</p>
          ) : (
            <p className="font-semibold text-coral-ink">{above.map(t => `${DOMAIN_NAMES[t.gid]} (${Math.round(t.avg)})`).join(', ')}</p>
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
              {['Prompt', 'Topic', 'Level', 'Change (T²)', 'PSI', 'PAI', 'Key gap', 'Pause', 'Word read longest', 'Compared with own prompts'].map(h => (
                <th key={h} scope="col" className="px-2.5 py-3 text-left whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {snapshots.map((snap, i) => {
              const lv     = snap.level || 'A'
              const noData = snap.flag === 'NO_DATA'
              const psi_v  = Number(snap.psi || 0)
              const pai_v  = Number(snap.pai || 0)
              const t2v    = Number(snap.t2_score || 0)
              const topHW  = (snap.hover_words || [])[0]
              const kind = psi_v > pai_v * 1.2 ? 'mostly slowing' : pai_v > psi_v * 1.2 ? 'mostly restlessness' : 'slowing and restlessness'
              const interp = noData ? (snap.typing_issue ? 'Not scored (typing looked automatic)' : 'No typing captured')
                : ownMedian > 0 && t2v >= 3 * ownMedian && t2v > 10 ? `Well above the client's other prompts (${kind})`
                : ownMedian > 0 && t2v >= 1.5 * ownMedian && t2v > 10 ? 'Above the client\'s other prompts'
                : 'Like the client\'s other prompts'
              return (
                <tr key={i} className={`border-t border-border/60 ${i % 2 === 1 ? 'bg-[#FAFCFC]' : 'bg-white'}`}>
                  <td className="px-2.5 py-2.5 font-bold text-tmain">{snap.item_id || '—'}</td>
                  <td className="px-2.5 py-2.5 text-tsub max-w-[120px] truncate" title={snap.group_name || ''}>{snap.group_name?.split(':')[1]?.trim() || '—'}</td>
                  <td className="px-2.5 py-2.5 font-semibold text-tmain">{lv}</td>
                  <td className="px-2.5 py-2.5 tabular-nums text-tmain">{noData ? '—' : t2v.toFixed(1)}</td>
                  <td className="px-2.5 py-2.5 tabular-nums text-tsub">{noData ? '—' : psi_v.toFixed(1)}</td>
                  <td className="px-2.5 py-2.5 tabular-nums text-tsub">{noData ? '—' : pai_v.toFixed(1)}</td>
                  <td className="px-2.5 py-2.5 tabular-nums text-tsub whitespace-nowrap">{noData ? '—' : `${Math.round((snap.flight_time || 0) * 1000)} ms`}</td>
                  <td className="px-2.5 py-2.5 tabular-nums text-tsub whitespace-nowrap">{snap.pre_typing_away ? 'away?' : `${(Math.round(snap.pre_typing_pause_ms || 0) / 1000).toFixed(1)} s`}</td>
                  <td className="px-2.5 py-2.5 text-tmain max-w-[120px] truncate">
                    {topHW ? <span className="font-medium">&ldquo;{topHW.word}&rdquo;</span> : <span className="text-tsub">—</span>}
                  </td>
                  <td className="px-2.5 py-2.5 text-tsub min-w-[170px]">{interp}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {itemP95 && (
        <p className="text-xs text-tsub mt-3">
          Healthy adults are compared on topic averages (above typical when higher than in 95% of healthy adults, T² &gt; {itemP95.toFixed(0)}).
          A single prompt varies too much for that comparison, so it is compared with this client's own other prompts.
        </p>
      )}
    </div>
  )
}


// Cursor movement while answering each questionnaire, next to the clicking
// warm-up. Descriptive only: there is no healthy reference for these ratios
// yet, and they are not part of the result. (The questionnaire movements also
// feed the session baseline, so the main score hardly reflects them.)
const CURSOR_ROWS = [
  { key: 'jerk',            label: 'Jerkiness',          hint: 'sudden changes of speed' },
  { key: 'path_entropy',    label: 'Direction changes',  hint: 'how scattered the path was' },
  { key: 'pause_frequency', label: 'Stops per second',   hint: 'cursor halts over 0.5 s' },
  { key: 'velocity',        label: 'Speed',              hint: 'pixels per second' },
]

export function CursorComparison({ cursor }) {
  const w = cursor?.warmup
  const cols = [['phq', 'PHQ-9'], ['gad', 'GAD-7']].filter(([k]) => cursor?.[k])
  if (!w || !cols.length) return <p className="text-sm text-tsub">Cursor movement was not recorded for this session.</p>
  const ratio = (v, b) => (b > 0 ? v / b : null)
  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-tsub border-b border-border">
              <th className="px-2.5 py-2 font-semibold">Measure</th>
              <th className="px-2.5 py-2 font-semibold">Clicking warm-up</th>
              {cols.map(([k, name]) => <th key={k} className="px-2.5 py-2 font-semibold">{name} (vs warm-up)</th>)}
            </tr>
          </thead>
          <tbody>
            {CURSOR_ROWS.map(r => (
              <tr key={r.key} className="border-b border-border/60">
                <td className="px-2.5 py-2.5"><span className="font-semibold text-tmain">{r.label}</span><span className="block text-xs text-tsub">{r.hint}</span></td>
                <td className="px-2.5 py-2.5 tabular-nums text-tmain">{Number(w[r.key] || 0).toFixed(r.key === 'velocity' || r.key === 'jerk' ? 0 : 2)}</td>
                {cols.map(([k]) => {
                  const v = Number(cursor[k][r.key] || 0), x = ratio(v, Number(w[r.key] || 0))
                  return (
                    <td key={k} className="px-2.5 py-2.5 tabular-nums text-tmain">
                      {v.toFixed(r.key === 'velocity' || r.key === 'jerk' ? 0 : 2)}
                      {x != null && <span className="text-tsub"> (×{x.toFixed(2)})</span>}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-tsub mt-3 max-w-[80ch]">
        Description only. Answering a questionnaire is a different task from clicking circles, and there is no healthy reference for these ratios yet,
        so they are not part of the result. Compare them across this client's sessions: a ratio that grows from visit to visit is worth asking about.
      </p>
    </div>
  )
}
