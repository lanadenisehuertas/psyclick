import { ShieldAlert, AlertTriangle, Eye, CheckCircle2 } from 'lucide-react'
import { MCID, ITEM9_LABEL, HEALTHY_GAP } from './text.js'

// Everything that stood out in one session, including signals too small to
// change the overall result. Early detection lives in these small signals.
const LEAN = { 'Psychomotor Retardation': 'slowing', 'Psychomotor Agitation': 'restlessness', 'Mixed Disturbance': 'both slowing and restlessness' }

const PHASE_NAME = { 'typing warm-up': 'the typing warm-up', 'clicking warm-up': 'the clicking warm-up', 'PHQ-9': 'PHQ-9', 'GAD-7': 'GAD-7' }
const phaseName = p => PHASE_NAME[p] || (p ? `prompt ${p}` : 'the session')
const minutes = s => (s >= 90 ? `${(s / 60).toFixed(1)} min` : `${Math.round(s)} s`)

export function collectSignals({ item9, phq, gad, t2, sP95, label, psiPct, paiPct, snapshots, iP95, levelT2, history, sessionId, quality, typing }) {
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

  // The first prompt also carries orientation time, so it is left out, and
  // a minute or more before typing is time away, not hesitation.
  const away = (snapshots || []).filter(s => s.pre_typing_away || (s.pre_typing_pause_ms || 0) >= 60000)
  if (away.length) add('note', `No typing for over a minute before ${away.map(s => s.item_id).join(', ')} — possibly time away rather than hesitation. Ask the client what happened.`)
  const pauses = (snapshots || []).slice(1).filter(s => !away.includes(s))
    .map(s => ({ id: s.item_id, p: (s.pre_typing_pause_ms || 0) / 1000 })).filter(x => x.p > 0)
  if (pauses.length >= 4) {
    const sorted = [...pauses].sort((a, b) => a.p - b.p)
    const median = sorted[Math.floor(sorted.length / 2)].p
    const longest = sorted[sorted.length - 1]
    if (longest.p >= Math.max(2 * median, median + 5)) add('note', `Long hesitation before prompt ${longest.id}: ${longest.p.toFixed(1)} s, against a typical ${median.toFixed(1)} s.`)
  }

  // Absolute typing speed against healthy adults. The own-baseline comparison
  // cannot see someone who was slow from the start, warm-up included.
  if (typing?.task_flight > HEALTHY_GAP.p95) {
    const slowFromStart = typing.warmup_flight && typing.warmup_flight >= 0.8 * typing.task_flight
    add('watch', `Typing in the written answers was slower than ${typing.task_flight > HEALTHY_GAP.p99 ? '99' : '95'}% of healthy adults `
      + `(${typing.task_flight.toFixed(2)} s between keys; most healthy adults ${HEALTHY_GAP.p25.toFixed(2)}–${HEALTHY_GAP.p75.toFixed(2)} s).`
      + (slowFromStart ? ' The warm-up was just as slow, so the comparison with the client\'s own baseline cannot show it. Consider typing experience, vision or motor problems, or general slowing.' : ''))
  }

  // Session quality: interruptions, focus, rushed questionnaires, skipped prompts
  const q = quality || {}
  const gaps = (q.interruptions || []).filter(x => x.kind === 'away')
  if (gaps.length) {
    const longest = gaps.reduce((a, b) => (b.seconds > a.seconds ? b : a))
    add('note', `Typing stopped ${gaps.length > 1 ? `${gaps.length} times` : 'once'} for ${minutes(longest.seconds)}${gaps.length > 1 ? ' at most' : ''} (during ${phaseName(longest.phase)}). That time was left out of every average.`)
  }
  const focus = (q.interruptions || []).filter(x => x.kind === 'focus')
  if (focus.length) add('note', `The PsyClick window lost focus ${focus.length > 1 ? `${focus.length} times` : 'once'} (${[...new Set(focus.map(x => phaseName(x.phase)))].join(', ')}). Nothing typed in other programs was recorded.`)
  for (const k of q.rushed || []) {
    const pace = q.pace_s_per_item?.[k]
    add('watch', `${k === 'phq' ? 'PHQ-9' : 'GAD-7'} was answered in about ${pace?.toFixed(1)} s per question — check that the questions were read; the score may not reflect how the client feels.`)
  }
  if ((q.answers_skipped || 0) >= 4) add('note', `${q.answers_skipped} of 12 written prompts were left blank.`)

  const odd = (snapshots || []).filter(s => s.typing_issue)
  if (odd.length) add('watch', `Typing on ${odd.map(s => s.item_id).join(', ')} looked ${odd.some(s => s.typing_issue === 'automatic') ? 'pasted or entered by another program' : 'like a held-down key'}, so ${odd.length > 1 ? 'those prompts were' : 'that prompt was'} not scored.`)

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
