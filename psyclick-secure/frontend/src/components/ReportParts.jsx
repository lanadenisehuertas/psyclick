import { useId, useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { ChevronDown, ArrowRight, ShieldCheck } from 'lucide-react'
import { FLAG_META, flagMeta } from '../lib/status.jsx'

const EASE = [0.22, 1, 0.36, 1]

// ── Status hero: the one thing to read first ────────────────────────────────
const BEHAVIOUR_ALONE = {
  GREEN: 'Behaviour on its own stayed within the healthy range.',
  AMBER: 'Behaviour on its own also changed more than in most healthy adults.',
  RED: 'Behaviour on its own also changed more than in almost all healthy adults.',
}

export function StatusHero({ flag, label, confidence, pattern, behaviourFlag, reasons = [], caveat, children }) {
  const m = flagMeta(flag, label)
  const Icon = m.icon
  const steps = ['GREEN', 'AMBER', 'RED']
  const insufficient = label === 'Insufficient Data'
  const current = flag === 'REPEAT' ? null : flag
  // The questionnaires or a self-harm answer raised the result above what
  // behaviour alone showed: say so, instead of describing a behaviour change.
  const raised = reasons.length > 0 && (behaviourFlag !== flag || insufficient)
  const headline = raised ? reasons[0].charAt(0).toUpperCase() + reasons[0].slice(1) : m.headline
  const meaning = raised
    ? [reasons.length > 1 ? `Also: ${reasons.slice(1).join('; ')}.` : '',
       insufficient ? 'Behaviour could not be assessed (not enough typing).' : BEHAVIOUR_ALONE[behaviourFlag] || ''].filter(Boolean).join(' ')
    : m.meaning
  const sure = confidence == null ? null
    : confidence >= 0.75 ? 'High' : confidence >= 0.5 ? 'Moderate' : 'Low'

  return (
    <motion.section
      aria-labelledby="result-heading"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: EASE }}
      className={`rounded-[20px] border p-6 print-avoid shadow-card ${m.soft}`}
    >
      <div className="flex flex-col lg:flex-row gap-6">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-tsub mb-3">Overall result</p>
          <div className="flex items-start gap-4">
            <span className={`flex-shrink-0 w-14 h-14 rounded-full flex items-center justify-center ${m.solid} text-white`}>
              <Icon size={30} aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h2 id="result-heading" className={`font-display text-[28px] font-semibold leading-tight ${m.ink}`}>{m.label}</h2>
              <p className="text-lg font-semibold text-tmain mt-0.5">{headline}</p>
              <p className="text-[15px] text-tsub mt-1.5 leading-relaxed max-w-[62ch]">{meaning}</p>
              {caveat && (
                <p className="text-[15px] text-amber-ink font-medium mt-2 leading-relaxed max-w-[62ch]">{caveat.text}</p>
              )}
              {pattern && pattern !== 'Normal' && pattern !== 'Insufficient Data' && (
                <p className="text-sm text-tmain mt-2">
                  {behaviourFlag === 'GREEN' || (!behaviourFlag && flag === 'GREEN')
                    ? <>Still within the healthy range, leaning towards <span className="font-semibold">{plainPattern(pattern)}</span>. Worth checking at the next visit.</>
                    : <>Pattern noticed: <span className="font-semibold">{plainPattern(pattern)}</span></>}
                </p>
              )}
            </div>
          </div>

          {/* Three-step scale, with words under every step */}
          <ol className="mt-6 grid grid-cols-3 gap-2" aria-label="Result scale">
            {steps.map(s => {
              const sm = FLAG_META[s]
              const SIcon = sm.icon
              const active = s === current
              return (
                <li
                  key={s}
                  aria-current={active ? 'step' : undefined}
                  className={`rounded-xl border px-3 py-2 flex items-center gap-2 text-sm transition-colors ${
                    active ? `${sm.chip} font-bold shadow-sm` : 'bg-white/60 border-border text-tsub'}`}
                >
                  <SIcon size={16} aria-hidden="true" />
                  <span>{sm.label}</span>
                  {active && <span className="sr-only">(this result)</span>}
                </li>
              )
            })}
          </ol>
        </div>

        <div className="lg:w-[340px] flex-shrink-0 rounded-xl bg-white/80 border border-[#D9E6EA] p-5 flex flex-col gap-4">
          <div>
            <p className="text-sm font-semibold text-[#0F2A33] mb-1.5">What to do next</p>
            <p className="text-[15px] text-tmain leading-relaxed flex gap-2">
              <ArrowRight size={18} className={`flex-shrink-0 mt-0.5 ${m.ink}`} aria-hidden="true" />
              {caveat?.next || m.next}
            </p>
          </div>
          {sure && !raised && (
            <div>
              <p className="text-sm font-semibold text-[#0F2A33] mb-1">How clear the pattern is</p>
              <p className="text-[15px] text-tmain"><span className="font-bold">{sure}</span> <span className="text-tsub">({Math.round(confidence * 100)}%)</span></p>
            </div>
          )}
          {children}
          <p className="text-xs text-tsub flex gap-1.5 items-start mt-auto">
            <ShieldCheck size={14} className="flex-shrink-0 mt-0.5" aria-hidden="true" />
            Decision support only — not a diagnosis. Combine with your clinical judgement.
          </p>
        </div>
      </div>
    </motion.section>
  )
}

export function plainPattern(label) {
  return {
    'Psychomotor Retardation': 'slowed responses',
    'Psychomotor Agitation': 'restless, irregular movement',
    'Mixed Disturbance': 'both slowing and restlessness',
  }[label] || label
}

// ── Section wrapper ──────────────────────────────────────────────────────────
export function Section({ title, subtitle, children, aside }) {
  return (
    <section className="space-y-3">
      <div className="flex items-end justify-between gap-4 px-1">
        <div>
          <h2 className="text-lg font-bold text-tmain">{title}</h2>
          {subtitle && <p className="text-sm text-tsub mt-0.5 max-w-[80ch]">{subtitle}</p>}
        </div>
        {aside}
      </div>
      {children}
    </section>
  )
}

// ── Collapsible section for specialist detail ────────────────────────────────
export function Collapsible({ title, summary, icon: Icon, defaultOpen = false, forceOpen = false, children }) {
  const [openState, setOpen] = useState(defaultOpen)
  const open = forceOpen || openState
  const id = useId()
  return (
    <div className="surface overflow-hidden print-avoid">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-4 px-6 py-4 text-left cursor-pointer hover:bg-[#F7FAFA] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-ink"
      >
        {Icon && (
          <span className="w-10 h-10 rounded-full border border-[#D9E6EA] text-[#0A6B80] flex items-center justify-center flex-shrink-0">
            <Icon size={20} aria-hidden="true" />
          </span>
        )}
        <span className="flex-1 min-w-0">
          <span className="block font-display font-semibold text-[#0F2A33]">{title}</span>
          {summary && <span className="block text-sm text-tsub mt-0.5">{summary}</span>}
        </span>
        <span className="text-sm font-medium text-accent-ink whitespace-nowrap" data-print-hide>{open ? 'Hide' : 'Show'}</span>
        <motion.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }} className="text-tsub">
          <ChevronDown size={20} aria-hidden="true" />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={id}
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="border-t border-border p-5">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Scale bar with labelled zones and a marker ───────────────────────────────
// zones: [{ to, label, tone }] in ascending order, last `to` = scale maximum.
const ZONE_TONE = {
  good:  'bg-success/25',
  mild:  'bg-[#FFE7A8]',
  warn:  'bg-amber/40',
  high:  'bg-coral/40',
}

export function ScaleBar({ value, zones, markerLabel, ariaLabel }) {
  const max = zones[zones.length - 1].to
  const pos = Math.max(0, Math.min(100, (value / max) * 100))
  let from = 0
  const widths = zones.map(z => { const w = ((z.to - from) / max) * 100; from = z.to; return w })
  // Narrow zones cannot hold a label under the bar: use a compact legend instead
  const compact = widths.some(w => w < 16)
  return (
    <div className="pt-7" role="img" aria-label={ariaLabel}>
      <div className="relative">
        <div className="flex h-3.5 rounded-full overflow-hidden ring-1 ring-black/5">
          {zones.map((z, i) => <div key={i} className={ZONE_TONE[z.tone]} style={{ width: `${widths[i]}%` }} />)}
        </div>
        <motion.div
          className="absolute -top-7 inset-x-0 pointer-events-none"
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15, ease: EASE }}
        >
          <span
            className="absolute top-0 text-[11px] font-bold text-white bg-tmain rounded-md px-1.5 py-0.5 whitespace-nowrap"
            style={{ left: `clamp(0px, calc(${pos}% - 20px), calc(100% - 40px))` }}
          >{markerLabel}</span>
          <span className="absolute top-[20px] w-0.5 h-[22px] bg-tmain" style={{ left: `calc(${pos}% - 1px)` }} />
        </motion.div>
      </div>
      {compact ? (
        <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-[11px] text-tsub">
          {zones.map((z, i) => (
            <span key={i} className="inline-flex items-center gap-1">
              <span className={`w-2.5 h-2.5 rounded-sm ${ZONE_TONE[z.tone]}`} aria-hidden="true" />{z.label}
            </span>
          ))}
        </div>
      ) : (
        <div className="flex mt-1.5 text-[11px] text-tsub">
          {zones.map((z, i) => (
            <span key={i} className="truncate pr-1" style={{ width: `${widths[i]}%` }} title={z.label}>{z.label}</span>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Result card ──────────────────────────────────────────────────────────────
export function ResultCard({ title, technical, value, valueSuffix, verdict, verdictTone = 'text-tmain', explain, info, children, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay, ease: EASE }}
      className="surface p-5 flex flex-col print-avoid"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-display font-semibold text-[#0F2A33] text-[16px] flex items-center">{title}{info}</h3>
          {technical && <p className="text-xs text-tsub mt-0.5">{technical}</p>}
        </div>
        <p className="font-mono text-2xl font-semibold text-[#0F2A33] tabular-nums whitespace-nowrap">
          {value}{valueSuffix && <span className="text-sm font-medium text-tsub ml-1">{valueSuffix}</span>}
        </p>
      </div>
      {verdict && <p className={`mt-2 text-sm font-semibold ${verdictTone}`}>{verdict}</p>}
      <div className="mt-1">{children}</div>
      {explain && <p className="text-sm text-tsub leading-relaxed mt-3 pt-3 border-t border-border/70">{explain}</p>}
    </motion.div>
  )
}
