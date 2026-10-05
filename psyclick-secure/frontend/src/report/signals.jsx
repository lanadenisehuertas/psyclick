import { ShieldAlert, AlertTriangle, Eye, CheckCircle2 } from 'lucide-react'
import { MCID, ITEM9_LABEL } from './text.js'

// Everything that stood out in one session, including signals too small to
// change the overall result. Early detection lives in these small signals.
const LEAN = { 'Psychomotor Retardation': 'slowing', 'Psychomotor Agitation': 'restlessness', 'Mixed Disturbance': 'both slowing and restlessness' }

export function collectSignals({ item9, phq, gad, t2, sP95, label, psiPct, paiPct, snapshots, iP95, levelT2, history, sessionId }) {
  const out = []
  const add = (level, text) => out.push({ level, text })

  if (item9 > 0) add('alert', `Thoughts of self-harm reported on PHQ-9 question 9 (“${ITEM9_LABEL[item9]}”).`)

  if (phq >= 10) add('watch', `Depression questionnaire in the ${phq >= 20 ? 'severe' : phq >= 15 ? 'moderately severe' : 'moderate'} range (PHQ-9 ${phq}).`)
  else if (phq >= 5) add('note', `Mild depressive symptoms reported (PHQ-9 ${phq}).`)
  if (gad >= 10) add('watch', `Anxiety questionnaire in the ${gad >= 15 ? 'severe' : 'moderate'} range (GAD-7 ${gad}).`)
  else if (gad >= 5) add('note', `Mild anxiety symptoms reported (GAD-7 ${gad}).`)

  if (t2 > sP95) add('watch', 'Typing and mouse behaviour shifted more than in 95% of healthy adults.')
  else if (t2 > sP95 * 0.8) add('note', 'Behaviour change was close to the healthy limit.')
  if (t2 > 0 && t2 <= sP95 && LEAN[label]) add('note', `Within the healthy range, but the change leaned towards ${LEAN[label]}.`)

  const idx = (pct, what) => {
    if (pct == null) return
    if (pct >= 95) add('watch', `${what} higher than ${pct >= 99.5 ? 'almost all' : `${Math.round(pct)}% of`} healthy adults.`)
    else if (pct >= 85) add('note', `${what} higher than ${Math.round(pct)}% of healthy adults.`)
  }
  idx(psiPct, 'Slowing')
  idx(paiPct, 'Restlessness')

  const scored = (snapshots || []).filter(s => s.flag !== 'NO_DATA')
  const above = scored.filter(s => Number(s.t2_score) > iP95)
  if (above.length) add(above.length >= 3 ? 'watch' : 'note', `${above.length} prompt${above.length > 1 ? 's' : ''} rose above the healthy range: ${above.map(s => s.item_id).join(', ')}.`)

  const la = levelT2?.A || 0, lb = levelT2?.B || 0, lc = levelT2?.C || 0
  if (lc > lb && lb > la && lc > 0) add('note', 'Change grew from mild to strong prompts — a reaction to emotional load.')

  // The first prompt also carries orientation time, so it is left out.
  const pauses = (snapshots || []).slice(1).map(s => ({ id: s.item_id, p: (s.pre_typing_pause_ms || 0) / 1000 })).filter(x => x.p > 0)
  if (pauses.length >= 4) {
    const sorted = [...pauses].sort((a, b) => a.p - b.p)
    const median = sorted[Math.floor(sorted.length / 2)].p
    const longest = sorted[sorted.length - 1]
    if (longest.p >= Math.max(2 * median, median + 5)) add('note', `Long hesitation before prompt ${longest.id}: ${longest.p.toFixed(1)} s, against a typical ${median.toFixed(1)} s.`)
  }

  const words = {}
  ;(snapshots || []).forEach(s => (s.hover_words || []).forEach(h => {
    const k = String(h.word).toLowerCase().replace(/[^a-z'’-]/g, '')
    if (k.length > 3) words[k] = (words[k] || 0) + (h.dwell_ms || 0)
  }))
  const topWord = Object.entries(words).sort((a, b) => b[1] - a[1])[0]
  if (topWord && topWord[1] >= 1500) add('note', `The cursor lingered longest on “${topWord[0]}” (${(topWord[1] / 1000).toFixed(1)} s).`)

  if (history && history.length > 1) {
    const ordered = [...history].sort((a, b) => a.session_id - b.session_id)
    const i = ordered.findIndex(s => String(s.session_id) === String(sessionId))
    if (i > 0) {
      const prev = ordered[i - 1], now = ordered[i]
      const dp = now.phq - prev.phq, dg = now.gad - prev.gad
      if (dp >= MCID.phq) add('watch', `PHQ-9 rose ${dp} points since the previous session.`)
      if (dg >= MCID.gad) add('watch', `GAD-7 rose ${dg} points since the previous session.`)
      if (t2 > sP95 && prev.t2 <= sP95 && now.t2 > sP95) add('watch', 'Behaviour moved above the healthy range since the previous session.')
    }
  }
  const order = { alert: 0, watch: 1, note: 2 }
  return out.sort((a, b) => order[a.level] - order[b.level])
}

const STYLE = {
  alert: { icon: ShieldAlert,   cls: 'text-coral-ink',  label: 'Act now',      row: 'bg-[#FBEDEC] border-[#F3C9C6]', chip: 'bg-coral-ink text-white' },
  watch: { icon: AlertTriangle, cls: 'text-amber-ink',  label: 'Watch',        row: 'bg-[#FEF5E6] border-[#F6DDB0]', chip: 'bg-[#FCE3B6] text-amber-ink' },
  note:  { icon: Eye,           cls: 'text-peri-ink',   label: 'Worth noting', row: 'bg-[#EEF3FB] border-[#D6E2F4]', chip: 'bg-[#DCE6F6] text-peri-ink' },
}

export function SignalsList({ signals }) {
  if (!signals.length) {
    return (
      <p className="flex items-center gap-2 text-success-ink font-semibold">
        <CheckCircle2 size={20} aria-hidden="true" /> Nothing stood out in this session.
      </p>
    )
  }
  return (
    <ul className="grid gap-2">
      {signals.map((s, i) => {
        const st = STYLE[s.level]
        return (
          <li key={i} className={`flex gap-3 items-start rounded-xl border px-3.5 py-2.5 ${st.row}`}>
            <st.icon size={18} className={`${st.cls} flex-shrink-0 mt-0.5`} aria-hidden="true" />
            <p className="text-[15px] text-tmain leading-snug flex-1">{s.text}</p>
            <span className={`text-[11px] font-semibold uppercase tracking-wide rounded-full px-2 py-0.5 whitespace-nowrap ${st.chip}`}>{st.label}</span>
          </li>
        )
      })}
    </ul>
  )
}
