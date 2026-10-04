import { CheckCircle2, AlertTriangle, AlertOctagon, HelpCircle, MinusCircle } from 'lucide-react'

// One vocabulary for session outcomes across the app. Every status carries an
// icon and words, so meaning never depends on colour alone.
export const FLAG_META = {
  GREEN: {
    label: 'No concerns',
    headline: 'Typing and mouse behaviour looked typical',
    meaning: 'This client behaved within the range seen in healthy adults during the emotional prompts.',
    next: 'No extra follow-up is needed from this screening. Continue routine care.',
    icon: CheckCircle2,
    chip: 'bg-success/15 text-success-ink border-success/30',
    soft: 'bg-success/10 border-success/30',
    ink: 'text-success-ink',
    solid: 'bg-success',
  },
  AMBER: {
    label: 'Follow up',
    headline: 'Some changes are worth discussing',
    meaning: "The client's behaviour moved further from their own baseline than most healthy adults do.",
    next: 'Plan a follow-up conversation within 48–72 hours, focused on the areas highlighted below.',
    icon: AlertTriangle,
    chip: 'bg-amber/15 text-amber-ink border-amber/40',
    soft: 'bg-amber/10 border-amber/40',
    ink: 'text-amber-ink',
    solid: 'bg-amber',
  },
  RED: {
    label: 'Review now',
    headline: 'Marked changes in behaviour',
    meaning: 'The change from the client’s own baseline is larger than in almost all healthy adults.',
    next: 'Carry out a structured risk assessment during this session. Do not defer.',
    icon: AlertOctagon,
    chip: 'bg-coral/15 text-coral-ink border-coral/40',
    soft: 'bg-coral/10 border-coral/40',
    ink: 'text-coral-ink',
    solid: 'bg-coral',
  },
  INSUFFICIENT: {
    label: 'Not enough data',
    headline: 'Not enough typing to assess behaviour',
    meaning: 'Too little keyboard activity was captured to compare against the baseline.',
    next: 'Repeat the session, or rely on the questionnaires and your clinical observation.',
    icon: HelpCircle,
    chip: 'bg-amber/15 text-amber-ink border-amber/40',
    soft: 'bg-amber/10 border-amber/40',
    ink: 'text-amber-ink',
    solid: 'bg-amber',
  },
  NO_DATA: {
    label: 'Not scored',
    icon: MinusCircle,
    chip: 'bg-border/60 text-tsub border-border',
    ink: 'text-tsub',
    solid: 'bg-border',
  },
}

export function flagMeta(flag, label = '') {
  if (label === 'Insufficient Data') return FLAG_META.INSUFFICIENT
  return FLAG_META[flag] || FLAG_META.GREEN
}

export function StatusBadge({ flag, label = '', size = 'sm' }) {
  const m = flagMeta(flag, label)
  const Icon = m.icon
  const pad = size === 'lg' ? 'px-3 py-1 text-sm gap-1.5' : 'px-2.5 py-0.5 text-xs gap-1'
  return (
    <span className={`inline-flex items-center rounded-full border font-semibold whitespace-nowrap ${pad} ${m.chip}`}>
      <Icon size={size === 'lg' ? 16 : 13} aria-hidden="true" />
      {m.label}
    </span>
  )
}

// Database timestamps arrive as "YYYY-MM-DD HH:MM:SS[.ffffff][+00]" (UTC).
export function parseTimestamp(ts) {
  if (!ts) return null
  let s = String(ts).trim().replace(' ', 'T')
  s = s.replace(/([+-]\d{2})$/, '$1:00')
  if (!/[zZ]|[+-]\d{2}:\d{2}$/.test(s)) s += 'Z'
  const d = new Date(s)
  return isNaN(d.getTime()) ? null : d
}

export function formatTimestamp(ts, opts) {
  const d = parseTimestamp(ts)
  return d ? d.toLocaleString(undefined, opts || { dateStyle: 'medium', timeStyle: 'short' }) : '—'
}
