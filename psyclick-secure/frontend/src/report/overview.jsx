import { motion } from 'motion/react'
import { Activity, CloudRain, Wind, MessagesSquare, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import { EASE } from '../components/ui.jsx'
import { MCID, ITEM9_LABEL, DOMAIN_NAMES, phqLabel, gadLabel } from './text.js'
import { topicAverages, topicSignal, byTime } from './visuals.jsx'

// ── Shared bits ─────────────────────────────────────────────────────────────
// Severity: 0 in range · 1 mild / worth noting · 2 watch · 3 high · 4 act now
const LEVEL = [
  { chip: 'In range',     cls: 'bg-[#DDF5EA] text-success-ink',   ring: '' },
  { chip: 'Worth noting', cls: 'bg-[#E3EBF8] text-peri-ink',      ring: '' },
  { chip: 'Watch',        cls: 'bg-[#FCEBD0] text-amber-ink',     ring: 'ring-2 ring-[#F5A623]/70' },
  { chip: 'High',         cls: 'bg-[#F9DCDA] text-coral-ink',     ring: 'ring-2 ring-[#F27C7C]/80' },
  { chip: 'Act now',      cls: 'bg-coral-ink text-white',         ring: 'ring-2 ring-coral-ink' },
]
// Card tints, all drawn from the logo: mint, cyan, periwinkle, deep blue
export const TINT = {
  mint: { bg: 'linear-gradient(150deg,#DFF8EE 0%,#F4FCF9 70%)', ink: '#127552', stroke: '#3CCB9A' },
  cyan: { bg: 'linear-gradient(150deg,#DCF4F8 0%,#F3FBFC 70%)', ink: '#0A6B80', stroke: '#2BB8CF' },
  peri: { bg: 'linear-gradient(150deg,#E2EBF8 0%,#F5F8FD 70%)', ink: '#3D5FA8', stroke: '#6F98D4' },
  deep: { bg: 'linear-gradient(150deg,#E4E8F6 0%,#F6F7FC 70%)', ink: '#2F4C8F', stroke: '#3D5FA8' },
}

export function Ring({ value, max, color, size = 64, label }) {
  const r = (size - 10) / 2, c = 2 * Math.PI * r
  const f = Math.max(0, Math.min(1, value / max))
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={label}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#FFFFFF" strokeWidth="8" />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#000" strokeOpacity=".05" strokeWidth="8" />
      <motion.circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`} strokeDasharray={c}
        initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - f) }} transition={{ duration: 0.9, ease: EASE, delay: 0.2 }} />
    </svg>
  )
}

// 1st, 2nd, 3rd … with “above 99th” for the very top
function pctLabel(p) {
  if (p >= 99.5) return 'top 1%'
  const n = Math.round(p), t = n % 100, u = n % 10
  const suf = t >= 11 && t <= 13 ? 'th' : u === 1 ? 'st' : u === 2 ? 'nd' : u === 3 ? 'rd' : 'th'
  return `${n}${suf} pct`
}

function Spark({ values, limit, color }) {
  const W = 120, H = 44, P = 4
  if (!values.length) return null
  const max = Math.max(limit ? limit * 1.15 : 0, ...values, 1)
  const x = i => P + (i * (W - 2 * P)) / Math.max(1, values.length - 1)
  const y = v => H - P - (v / max) * (H - 2 * P)
  const d = values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ')
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
      {limit && <rect x={P} y={y(limit)} width={W - 2 * P} height={H - P - y(limit)} rx="3" fill="#FFFFFF" opacity=".75" />}
      {limit && <line x1={P} x2={W - P} y1={y(limit)} y2={y(limit)} stroke="#B83A38" strokeOpacity=".5" strokeDasharray="3 3" />}
      <motion.path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1, ease: EASE, delay: 0.2 }} />
      {limit && values.map((v, i) => v > limit && <circle key={i} cx={x(i)} cy={y(v)} r="2.8" fill="#B83A38" />)}
    </svg>
  )
}

function Segments({ parts, size = 64, label }) {
  const total = parts.reduce((a, p) => a + p.n, 0) || 1
  const r = (size - 10) / 2, c = 2 * Math.PI * r
  let acc = 0
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={label}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#FFFFFF" strokeWidth="8" />
      {parts.filter(p => p.n > 0).map((p, i) => {
        const len = (p.n / total) * c
        const el = (
          <motion.circle key={i} cx={size / 2} cy={size / 2} r={r} fill="none" stroke={p.color} strokeWidth="8"
            transform={`rotate(${-90 + (acc / c) * 360} ${size / 2} ${size / 2})`}
            initial={{ strokeDasharray: `0 ${c}` }} animate={{ strokeDasharray: `${Math.max(0, len - 2)} ${c}` }}
            transition={{ duration: 0.7, ease: EASE, delay: 0.25 + i * 0.1 }} />
        )
        acc += len
        return el
      })}
    </svg>
  )
}

function Delta({ d, mcid, unit = '', higherIsWorse = true, first }) {
  if (first) return <span className="text-tsub">First session · today is the baseline</span>
  if (d == null) return <span className="text-tsub">No earlier session to compare</span>
  const big = mcid != null && Math.abs(d) >= mcid
  const worse = higherIsWorse ? d > 0 : d < 0
  const Icon = d > 0 ? ArrowUpRight : d < 0 ? ArrowDownRight : Minus
  const cls = d === 0 ? 'text-tsub' : big && worse ? 'text-coral-ink font-semibold' : big ? 'text-success-ink font-semibold' : 'text-tsub'
  return (
    <span className={`inline-flex items-center gap-1 ${cls}`}>
      <Icon size={14} aria-hidden="true" />
      {d > 0 ? '+' : ''}{d}{unit} since last session{big ? (worse ? ' · meaningful rise' : ' · meaningful drop') : ''}
    </span>
  )
}

function Kpi({ k, i }) {
  const t = TINT[k.tint]
  const L = LEVEL[k.level]
  return (
    <motion.article layout initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.06 * i, ease: EASE }}
      className={`relative h-full flex flex-col rounded-[20px] border border-white/70 p-5 shadow-card print-avoid ${L.ring}`} style={{ background: t.bg }}
      aria-label={`${k.title}: ${k.value}${k.suffix || ''}. ${L.chip}.`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-tmain flex items-center gap-1.5">{k.title}</p>
          <p className="text-[12px] text-tsub">{k.tech}</p>
        </div>
        <span className="w-10 h-10 rounded-full bg-white/90 border border-white flex items-center justify-center flex-shrink-0 shadow-sm" style={{ color: t.ink }}>
          <k.icon size={19} aria-hidden="true" />
        </span>
      </div>
      <div className="mt-3 flex items-center justify-between gap-3 min-h-[64px]">
        <p className="font-display font-semibold text-tmain leading-none whitespace-nowrap">
          <span className="text-[38px] tabular-nums">{k.value}</span>
          {k.suffix && <span className="text-base text-tsub font-medium ml-1">{k.suffix}</span>}
        </p>
        <div className="flex-shrink-0">{k.visual}</div>
      </div>
      <p className="mt-1 text-sm font-semibold flex-1" style={{ color: t.ink }}>{k.verdict}</p>
      <div className="mt-3 pt-3 border-t border-black/[0.06] flex flex-wrap items-center justify-between gap-2 text-[12.5px]">
        {k.delta}
        <span className={`px-2 py-0.5 rounded-full text-[11.5px] font-semibold ${L.cls}`}>{L.chip}</span>
      </div>
      {k.extra && <p className="mt-2 text-[12.5px] font-semibold text-coral-ink">{k.extra}</p>}
    </motion.article>
  )
}

// ── Headline numbers, most urgent first ─────────────────────────────────────
export function KpiStrip({ t2, sP95, sP99, insufficient, phq, gad, item9, snapshots, iP95, iP99, history, sessionId }) {
  const ordered = Array.isArray(history) ? [...history].sort(byTime) : null
  const idx = ordered ? ordered.findIndex(s => String(s.session_id) === String(sessionId)) : -1
  const prev = idx > 0 ? ordered[idx - 1] : null
  const first = idx === 0
  const delta = (key, mcid, unit) => <Delta first={first} d={prev ? Math.round(Number(ordered[idx][key] || 0) - Number(prev[key] || 0)) : null} mcid={mcid} unit={unit} />

  const scored = (snapshots || []).filter(s => s.flag !== 'NO_DATA')
  const vals = scored.map(s => Number(s.t2_score) || 0)
  // Topics, not single prompts, are compared with the healthy topic limits
  const topicList = topicAverages(snapshots)
  const ts = topicSignal(topicList, iP95, iP99)
  const nHigh = ts.far.length
  const nAbove = ts.above.length
  const nIn = topicList.length - nAbove

  const t2Level = insufficient ? 1 : t2 > sP99 ? 3 : t2 > sP95 ? 2 : t2 > 0.8 * sP95 ? 1 : 0
  const phqLevel = item9 > 0 ? 4 : phq >= 15 ? 3 : phq >= 10 ? 2 : phq >= 5 ? 1 : 0
  const gadLevel = gad >= 15 ? 3 : gad >= 10 ? 2 : gad >= 5 ? 1 : 0
  const promptLevel = insufficient || !topicList.length ? 0 : nHigh ? 3 : ts.flagged ? 2 : nAbove ? 1 : 0

  const cards = [
    {
      key: 't2', tint: 'cyan', icon: Activity, level: t2Level,
      title: 'Behaviour change', tech: insufficient ? 'Typing & mouse vs. own warm-up (T²)' : `T² vs. own warm-up · healthy limit ${Math.round(sP95)}`,
      value: insufficient ? '—' : Math.round(t2), suffix: '',
      verdict: insufficient ? 'Not enough typing to score' : t2 > sP99 ? 'Much higher than healthy adults' : t2 > sP95 ? 'Higher than most healthy adults' : 'Within the healthy range',
      visual: insufficient ? null : <Spark values={vals} color={TINT.cyan.stroke} />,
      delta: insufficient ? <span className="text-tsub">Repeat the behavioural part</span> : delta('t2', null),
    },
    {
      key: 'phq', tint: 'mint', icon: CloudRain, level: phqLevel,
      title: 'Depression', tech: 'PHQ-9 · last 2 weeks',
      value: phq, suffix: '/ 27', verdict: `${phqLabel(phq)} symptoms`,
      visual: <Ring value={phq} max={27} color={phq >= 15 ? '#E0605E' : phq >= 10 ? '#F5A623' : TINT.mint.stroke} label={`PHQ-9 ${phq} of 27`} />,
      delta: delta('phq', MCID.phq),
      extra: item9 > 0 ? `Question 9 (self-harm): “${ITEM9_LABEL[item9]}”` : null,
    },
    {
      key: 'gad', tint: 'peri', icon: Wind, level: gadLevel,
      title: 'Anxiety', tech: 'GAD-7 · last 2 weeks',
      value: gad, suffix: '/ 21', verdict: `${gadLabel(gad)} symptoms`,
      visual: <Ring value={gad} max={21} color={gad >= 15 ? '#E0605E' : gad >= 10 ? '#F5A623' : TINT.peri.stroke} label={`GAD-7 ${gad} of 21`} />,
      delta: delta('gad', MCID.gad),
    },
    {
      key: 'prompts', tint: 'deep', icon: MessagesSquare, level: promptLevel,
      title: 'Topics that stood out', tech: 'Topic averages above healthy adults',
      value: insufficient || !topicList.length ? '—' : nAbove, suffix: insufficient || !topicList.length ? '' : `of ${topicList.length}`,
      verdict: insufficient || !topicList.length ? 'Not scored' : !nAbove ? 'All within the healthy range'
        : (ts.far.length ? ts.far : ts.above).map(t => DOMAIN_NAMES[t.gid]).join(', '),
      visual: insufficient || !vals.length ? null : (
        <Segments label={`${nIn} topics within, ${nAbove - nHigh} above, ${nHigh} far above`}
          parts={[{ n: nIn, color: '#8FB3E3' }, { n: nAbove - nHigh, color: '#F5A623' }, { n: nHigh, color: '#E0605E' }]} />
      ),
      delta: <span className="text-tsub">See the session trace below</span>,
    },
  ]
  // Most urgent first; ties keep the reading order above
  const sorted = cards.map((c, i) => ({ c, i })).sort((a, b) => b.c.level - a.c.level || a.i - b.i).map(x => x.c)

  return (
    <div className="grid sm:grid-cols-2 xl:grid-cols-4 print:grid-cols-4 gap-4" role="list" aria-label="Headline results, most urgent first">
      {sorted.map((k, i) => <div role="listitem" key={k.key} className="h-full"><Kpi k={k} i={i} /></div>)}
    </div>
  )
}

// ── Profile against healthy adults (radar) ──────────────────────────────────
const AXES = [
  { key: 't2_score',  name: 'Behaviour change' },
  { key: 'psi',       name: 'Slowing' },
  { key: 'pai',       name: 'Restlessness' },
  { key: 'gad_score', name: 'Anxiety' },
  { key: 'phq_score', name: 'Depression' },
]

export function ProfileRadar({ metrics, insufficient }) {
  const axes = AXES.filter(a => metrics?.[a.key] && !(insufficient && ['t2_score', 'psi', 'pai'].includes(a.key)))
  if (axes.length < 3) {
    return <p className="text-sm text-tsub">The profile needs the behavioural scores, which were not available for this session.</p>
  }
  const S = 300, C = S / 2, R = 108
  const pt = (i, f) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / axes.length
    return [C + Math.cos(a) * R * f, C + Math.sin(a) * R * f]
  }
  const poly = f => axes.map((_, i) => pt(i, f).map(v => v.toFixed(1)).join(',')).join(' ')
  const pcts = axes.map(a => Math.max(0, Math.min(100, Number(metrics[a.key].pct))))
  const client = pcts.map((p, i) => pt(i, Math.max(0.04, p / 100)).map(v => v.toFixed(1)).join(',')).join(' ')
  const dot = p => (p >= 95 ? '#E0605E' : p >= 85 ? '#F5A623' : '#3CCB9A')
  const summary = axes.map((a, i) => `${a.name} ${pctLabel(pcts[i]).replace('pct', 'percentile')}`).join(', ')

  return (
    <div>
      <svg viewBox={`-60 -10 ${S + 120} ${S + 20}`} className="w-full max-w-[440px] mx-auto block" role="img"
        aria-label={`Client profile against healthy adults: ${summary}.`}>
        <defs>
          <linearGradient id="pr-fill" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#68D8E8" stopOpacity=".42" />
            <stop offset="1" stopColor="#78A8D8" stopOpacity=".42" />
          </linearGradient>
        </defs>
        <polygon points={poly(1)} fill="#FBE3E1" />
        <polygon points={poly(0.95)} fill="#FCEFD9" />
        <polygon points={poly(0.85)} fill="#E3F7EF" />
        {[0.25, 0.5, 0.75].map(f => <polygon key={f} points={poly(f)} fill="none" stroke="#CFE5DD" strokeWidth="1" />)}
        <polygon points={poly(0.85)} fill="none" stroke="#3CCB9A" strokeWidth="1.2" strokeDasharray="4 3" />
        {axes.map((_, i) => { const [x, y] = pt(i, 1); return <line key={i} x1={C} y1={C} x2={x} y2={y} stroke="#D9E6EA" /> })}
        <motion.polygon points={client} fill="url(#pr-fill)" stroke="#3D5FA8" strokeWidth="2.2" strokeLinejoin="round"
          style={{ originX: `${C}px`, originY: `${C}px` }}
          initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: 'spring', stiffness: 120, damping: 16, delay: 0.2 }} />
        {pcts.map((p, i) => { const [x, y] = pt(i, Math.max(0.04, p / 100)); return <circle key={i} cx={x} cy={y} r="5" fill={dot(p)} stroke="#fff" strokeWidth="2" /> })}
        {axes.map((a, i) => {
          const [x, y0] = pt(i, 1.16)
          const anchor = Math.abs(x - C) < 8 ? 'middle' : x > C ? 'start' : 'end'
          const y = y0 < C - R * 0.5 ? y0 - 16 : y0 > C + R * 0.5 ? y0 + 4 : y0 - 6
          return (
            <text key={a.key} x={x} y={y} textAnchor={anchor} dominantBaseline="middle" className="font-sans">
              <tspan x={x} fontSize="14" fontWeight="600" fill="#0F2A33">{a.name}</tspan>
              <tspan x={x} dy="17" fontSize="13" fill={dot(pcts[i]) === '#3CCB9A' ? '#127552' : dot(pcts[i]) === '#F5A623' ? '#9A5B00' : '#B83A38'} fontWeight="600">{pctLabel(pcts[i])}</tspan>
            </text>
          )
        })}
      </svg>
      <div className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1.5 text-xs text-tsub">
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-[#E3F7EF] border border-[#3CCB9A]" />Where 85% of healthy adults sit</span>
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-[#FCEFD9]" />Top 15%</span>
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-[#FBE3E1]" />Top 5%</span>
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm" style={{ background: 'linear-gradient(135deg,#68D8E8,#78A8D8)' }} />This client</span>
      </div>
    </div>
  )
}
