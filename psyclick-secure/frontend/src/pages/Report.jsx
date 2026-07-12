import { useEffect, useState, useRef, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Download, AlertTriangle, CheckCircle, Info } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'
import Sidebar from '../components/Sidebar.jsx'
import AnimatedBackground from '../components/AnimatedBackground.jsx'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'

// ── Clinical glossary ─────────────────────────────────────────────────────────
const GLOSSARY = {
  T2: {
    title: "Hotelling T² Score",
    what: "How much the patient's typing + mouse behavior shifted from their own baseline today.",
    flag: "Above threshold = significant deviation vs. this patient's own calibration (ipsative). Note: even healthy people regularly exceed the within-session threshold due to the novelty effect of emotional prompts — use the Population Comparison z-score for inter-individual context.",
    how: "Multivariate distance formula (T² = n·Δx·S⁻¹·Δx). Threshold = chi-squared critical at p=0.05.",
  },
  PSI: {
    title: "Psychomotor Slowing Index (PSI)",
    what: "Composite index of motor slowing — elevated flight time, dwell time, and pause frequency relative to the client's own EWMA calibration baseline. Operationalizes psychomotor retardation (depression-linked inhibition).",
    flag: "Ipsative thresholds (vs. own baseline): PSI > 0.5 mild · > 2.0 moderate · > 4.0 severe. When Population Comparison data is available, prefer the normative z-score: PSI accumulates naturally even in healthy people across 11 prompts, so z > +1.5 is the meaningful clinical signal. Pools feature contributions from flight time, dwell time, and pause frequency (Thesis §1.2).",
    how: "Cᵢ = (xᵢ − μᵢ) × [S⁻¹ · (x − μ)]ᵢ summed over PSI features (flight_time, dwell_time, pause_frequency) where diff > 0 (Mason & Young, 2002).",
  },
  PAI: {
    title: "Psychomotor Agitation Index (PAI)",
    what: "Composite index of motor agitation — elevated path entropy, cursor jerk, error rate, and cursor velocity relative to the client's own EWMA calibration baseline. Operationalizes psychomotor agitation (anxiety-linked erratic movement).",
    flag: "Ipsative thresholds (vs. own baseline): PAI > 0.5 mild · > 2.0 moderate · > 4.0 severe. When Population Comparison data is available, prefer the normative z-score: PAI accumulates naturally even in healthy people across 11 prompts, so z > +1.5 is the meaningful clinical signal. Pools feature contributions from path entropy, jerk, error rate, cursor velocity, and typing velocity (Thesis §1.2).",
    how: "Cᵢ = (xᵢ − μᵢ) × [S⁻¹ · (x − μ)]ᵢ summed over PAI features (path_entropy, jerk, error_rate, cursor_velocity, typing_velocity). All contributions summed regardless of direction.",
  },
  DomainT2: {
    title: "Domain T² Scores",
    what: "Which emotional theme triggered the most body-language change. 4 domains: Time/Workload, Interpersonal, Academic, Self-Evaluation.",
    flag: "Highest bar = primary clinical target. Self-Eval spikes carry highest suicide-risk correlation. Interpersonal spikes suggest attachment issues.",
    how: "Mean T² of 3 prompts within each domain (Levels A, B, C).",
  },
  LevelABC: {
    title: "Emotional Load Levels A / B / C",
    what: "Each domain is tested at 3 intensities: A (mild) → B (moderate) → C (high stress).",
    flag: "A→B→C rising = patient is genuinely reactive to emotional load (strong validity). Flat or reversed = interpret with caution.",
    how: "Mean T² across all 4 domains at each stress level. Level C uses the most emotionally activating phrasing.",
  },
  Flag: {
    title: "Clinical Risk Flag",
    what: "Overall session summary: GREEN = within normal · AMBER = follow up within 72h · RED = act same session.",
    flag: "RED requires structured risk assessment now. This system supports — not replaces — clinical judgment.",
    how: "Fuzzy logic combining T²/threshold ratio, PSI/PAI magnitude, and PHQ-9/GAD-7 severity bands.",
  },
  Spectrogram: {
    title: "Keystroke Interval Spectrogram",
    what: "Each bar = time between consecutive keystrokes (flight time in ms). Shows typing rhythm across the session.",
    flag: "Tall irregular bars = anxiety-driven disruption. Very tall uniform bars = depressive slowing. Smooth consistent bars = normal baseline.",
    how: "Consecutive inter-keystroke intervals from the emotional response task, displayed in sequence order.",
  },
}

// ── Reusable hover tooltip ────────────────────────────────────────────────────
function InfoTooltip({ glossaryKey, side = 'bottom' }) {
  const [visible, setVisible] = useState(false)
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const btnRef = useRef(null)
  const entry = GLOSSARY[glossaryKey]
  if (!entry) return null

  function show() {
    const rect = btnRef.current?.getBoundingClientRect()
    if (rect) {
      const x = Math.min(rect.left, window.innerWidth - 344)
      const y = side === 'top' ? rect.top - 8 : rect.bottom + 8
      setPos({ x, y, above: side === 'top' })
    }
    setVisible(true)
  }

  return (
    <span className="relative inline-flex" style={{ verticalAlign: 'middle' }}>
      <button
        ref={btnRef}
        type="button"
        onMouseEnter={show}
        onMouseLeave={() => setVisible(false)}
        className="ml-1 text-tsub/60 hover:text-accent transition-colors focus:outline-none"
        aria-label={`What is ${entry.title}?`}
      >
        <Info size={12} />
      </button>
      {visible && (
        <div
          className="fixed z-[9999] w-[320px] rounded-2xl shadow-2xl text-left overflow-hidden"
          style={{
            left: pos.x,
            top: pos.above ? undefined : pos.y,
            bottom: pos.above ? window.innerHeight - pos.y + 8 : undefined,
            background: 'linear-gradient(135deg, #0D2D2D 0%, #0a3d3d 100%)',
            border: '1px solid rgba(10,191,188,0.2)',
          }}
          onMouseEnter={() => setVisible(true)}
          onMouseLeave={() => setVisible(false)}
        >
          <div className="px-4 py-2.5 border-b border-white/10 bg-accent/10">
            <p className="font-bold text-[13px] text-accent">{entry.title}</p>
          </div>
          <div className="px-4 py-3 space-y-2.5">
            <div>
              <p className="text-[9px] font-bold uppercase tracking-widest text-white/40 mb-0.5">What it means</p>
              <p className="text-[11px] text-white/90 leading-snug">{entry.what}</p>
            </div>
            <div>
              <p className="text-[9px] font-bold uppercase tracking-widest text-white/40 mb-0.5">Clinical reading</p>
              <p className="text-[11px] text-white/90 leading-snug">{entry.flag}</p>
            </div>
            <div>
              <p className="text-[9px] font-bold uppercase tracking-widest text-white/40 mb-0.5">How it's computed</p>
              <p className="text-[11px] text-white/70 leading-snug">{entry.how}</p>
            </div>
          </div>
        </div>
      )}
    </span>
  )
}

// ── Design tokens ────────────────────────────────────────────────────────────
const FLAG_STYLE = {
  GREEN: { bg: 'bg-success/15 border-success/30', text: 'text-success', icon: CheckCircle,  label: 'No Significant Concerns' },
  AMBER: { bg: 'bg-amber/15  border-amber/30',   text: 'text-amber',   icon: AlertTriangle, label: 'Moderate Concerns'       },
  RED:   { bg: 'bg-coral/15  border-coral/30',   text: 'text-coral',   icon: AlertTriangle, label: 'Significant Concerns'    },
}

const DOMAIN_NAMES  = { 1: 'Time/Workload', 2: 'Interpersonal', 3: 'Academic', 4: 'Self-Eval' }
const DOMAIN_COLORS = { 1: '#5BA4CF', 2: '#0ABFBC', 3: '#36C98E', 4: '#F27C7C' }
const DOMAIN_BG     = { 1: '#EFF6FF', 2: '#E0FAFA', 3: '#ECFDF5', 4: '#FFF0F0' }
const LEVEL_COLORS  = { A: '#36C98E', B: '#F5A623', C: '#F27C7C' }

// ── Label helpers ────────────────────────────────────────────────────────────
function phqLabel(s) {
  if (s <= 4)  return 'Minimal'
  if (s <= 9)  return 'Mild'
  if (s <= 14) return 'Moderate'
  if (s <= 19) return 'Mod-Severe'
  return 'Severe'
}
function gadLabel(s) {
  if (s <= 4)  return 'Minimal'
  if (s <= 9)  return 'Mild'
  if (s <= 14) return 'Moderate'
  return 'Severe'
}

// ── Interpretation helpers ────────────────────────────────────────────────────
function t2Interp(t2, thr) {
  if (!thr || thr === Infinity) return 'Insufficient baseline data.'
  const r = t2 / thr
  if (r <= 1.0) return `Within normal range vs. own baseline (${r.toFixed(2)}× threshold).`
  if (r <= 1.5) return `Moderately elevated vs. own baseline (${r.toFixed(2)}× threshold). See Population Comparison for context.`
  return `Significantly elevated vs. own baseline (${r.toFixed(2)}× threshold). See Population Comparison z-score for clinical context.`
}
// psiInterp / paiInterp accept an optional normZ (z-score vs normative population).
// When normZ is provided, interpretation is driven by population standing rather than
// ipsative absolute thresholds — because PSI/PAI naturally accumulate even in healthy
// people across an 11-prompt session, so absolute values alone are not reliable indicators.
function psiInterp(v, normZ) {
  if (normZ !== undefined) {
    if (Math.abs(normZ) < 0.5)  return `Within typical range of the normative population (z=${normZ > 0 ? '+' : ''}${normZ.toFixed(2)}). Ipsative value ${v.toFixed(2)} is normal relative to healthy baseline.`
    if (normZ >= 1.5)  return `Significantly above normative mean (z=+${normZ.toFixed(2)}). Marked psychomotor slowing relative to healthy population — clinically significant.`
    if (normZ >= 1.0)  return `Moderately above normative mean (z=+${normZ.toFixed(2)}). Some slowing relative to healthy population. Monitor closely.`
    if (normZ <= -1.0) return `Below normative mean (z=${normZ.toFixed(2)}). Faster than average healthy population — no slowing concern.`
    return `Within normal population range (z=${normZ > 0 ? '+' : ''}${normZ.toFixed(2)}). No clinically significant slowing relative to healthy baseline.`
  }
  // Fallback: ipsative absolute thresholds (no normative data available)
  if (v < 0.5) return 'Within ipsative range. No psychomotor slowing vs. own baseline.'
  if (v < 2.0) return 'Mildly elevated vs. own baseline. Some psychomotor slowing observed.'
  if (v < 4.0) return 'Moderately elevated vs. own baseline. Clear slowing pattern — consistent with depressive inhibition.'
  return 'Elevated vs. own baseline. Marked slowing detected. Load Population Comparison for normative context.'
}
function paiInterp(v, normZ) {
  if (normZ !== undefined) {
    if (Math.abs(normZ) < 0.5)  return `Within typical range of the normative population (z=${normZ > 0 ? '+' : ''}${normZ.toFixed(2)}). Ipsative value ${v.toFixed(2)} is normal relative to healthy baseline.`
    if (normZ >= 1.5)  return `Significantly above normative mean (z=+${normZ.toFixed(2)}). Highly irregular motor pattern relative to healthy population — clinically significant agitation.`
    if (normZ >= 1.0)  return `Moderately above normative mean (z=+${normZ.toFixed(2)}). Elevated cursor irregularity relative to healthy population.`
    if (normZ <= -1.0) return `Below normative mean (z=${normZ.toFixed(2)}). More regular than average healthy population — no agitation concern.`
    return `Within normal population range (z=${normZ > 0 ? '+' : ''}${normZ.toFixed(2)}). No clinically significant agitation relative to healthy baseline.`
  }
  // Fallback: ipsative absolute thresholds (no normative data available)
  if (v < 0.5) return 'Within ipsative range. No agitation vs. own baseline.'
  if (v < 2.0) return 'Mildly elevated vs. own baseline. Slight cursor irregularity.'
  if (v < 4.0) return 'Moderately elevated vs. own baseline. Erratic movements consistent with anxiety-driven hyperarousal.'
  return 'Elevated vs. own baseline. Irregular motor pattern detected. Load Population Comparison for normative context.'
}

// ── Clinical recommendations (ported from Python _clinical_recs) ─────────────
function clinicalRecs(flag, label = '', psi = 0, pai = 0, phq = 0, gad = 0, domainT2 = {}, levelT2 = {}) {
  const recs = []
  label = label || ''

  if (flag === 'RED') {
    recs.push({ title: 'Immediate Safety Assessment',
      desc: `RED flag with PHQ-9=${phq} (${phqLabel(phq)}) and GAD-7=${gad} (${gadLabel(gad)}) warrants same-session structured risk assessment. Do not defer.` })
  } else if (flag === 'AMBER') {
    recs.push({ title: 'Schedule Follow-Up Within 48–72 Hours',
      desc: 'Moderate psychomotor deviation detected. Prioritize structured interview targeting the flagged domain before the next scheduled session.' })
  } else {
    recs.push({ title: 'Continue Routine Monitoring',
      desc: 'Psychomotor behavior within normal range for this client. Maintain current session frequency.' })
  }

  if (label.includes('Retardation') || psi > pai * 1.3) {
    recs.push({ title: 'Psychomotor Retardation — Administer MADRS',
      desc: `PSI=${psi.toFixed(3)} dominates. Keystroke latency and pause frequency significantly elevated. This sub-clinical motor inhibition pattern precedes observable psychomotor retardation. Administer MADRS (Items 6 & 7) and assess energy, anergia, and psychic slowing explicitly.` })
  } else if (label.includes('Agitation') || pai > psi * 1.3) {
    recs.push({ title: 'Psychomotor Agitation — Administer HAM-A',
      desc: `PAI=${pai.toFixed(3)} dominates. Cursor jerk and path irregularity elevated below observable threshold. This pattern typically precedes visible restlessness. Assess sleep onset, muscular tension, and concentration using HAM-A Items 1–4.` })
  } else if (label.includes('Mixed')) {
    recs.push({ title: 'Mixed Disturbance — Consider MDQ Screen',
      desc: `PSI=${psi.toFixed(3)} and PAI=${pai.toFixed(3)} both elevated concurrently. Mixed psychomotor state is a key indicator of bipolar spectrum disorder, agitated MDD, or complex PTSD. Administer MDQ and conduct mood episode timeline review.` })
  }

  if (phq >= 20) {
    recs.push({ title: 'Severe Depression — Pharmacotherapy Discussion',
      desc: `PHQ-9=${phq}/27. Severe range. Combined with biometric psychomotor slowing, this warrants antidepressant review or initiation. Assess suicidality (PHQ-9 Item 9). Document with date and score for longitudinal tracking.` })
  } else if (phq >= 15) {
    recs.push({ title: 'Moderately Severe Depression — Structured Evaluation',
      desc: `PHQ-9=${phq}/27. Warrants structured psychiatric evaluation. Cross-validate with HDRS if biometric slowing is present.` })
  }

  if (gad >= 15) {
    recs.push({ title: 'Severe Anxiety — Anxiolytic Review',
      desc: `GAD-7=${gad}/21. Severe range. Assess panic history, avoidance patterns, and safety behaviors. Consider buspirone or SSRI discussion. Corroborate with elevated PAI in biometric profile.` })
  } else if (gad >= 10) {
    recs.push({ title: 'Moderate Anxiety — CBT Referral',
      desc: `GAD-7=${gad}/21. CBT-targeted worry exposure and relaxation training indicated.` })
  }

  const domEntries = Object.entries(domainT2)
  if (domEntries.length > 0) {
    const [peakGid, peakVal] = domEntries.reduce((best, cur) => Number(cur[1]) > Number(best[1]) ? cur : best)
    const names = { 1: 'Time Pressure & Workload', 2: 'Interpersonal Friction', 3: 'Academic & Performance Pressure', 4: 'Self-Evaluation & Identity' }
    const tips  = {
      1: 'Explore task-overload schema and perfectionism-driven urgency. Assess for Type-A behavioral patterns, occupational burnout (MBI), and executive function deficits.',
      2: 'Explore attachment disruptions and relational schemas. Assess for rejection sensitivity and interpersonal hypersensitivity. Consider IIP-32 for interpersonal problem profiling.',
      3: 'Explore performance schema and evaluation-related threat. Assess for social anxiety disorder, impostor phenomenon, and achievement-based self-worth. Consider LSAS if social anxiety is suspected.',
      4: 'Strongest signal is in identity/self-evaluation — highest clinical concern. Explore core beliefs (Beck\'s cognitive triad: self, world, future). Self-critical cognition at this intensity correlates with suicidality and treatment resistance. Administer DAS-24 or BDI Item 5.',
    }
    if (Number(peakVal) > 0.3) {
      recs.push({ title: `Peak Domain: ${names[Number(peakGid)] || '?'} (T²=${Number(peakVal).toFixed(3)})`,
        desc: `This domain produced the highest psychomotor deviation in the session. ${tips[Number(peakGid)] || ''}` })
    }
  }

  const la = levelT2.A || 0, lb = levelT2.B || 0, lc = levelT2.C || 0
  if (lc > lb && lb > la && lc > 0.3) {
    recs.push({ title: 'Dose-Response Escalation — High Clinical Validity',
      desc: `T² increases monotonically A→B→C (A=${la.toFixed(2)}, B=${lb.toFixed(2)}, C=${lc.toFixed(2)}). This is the strongest internal validity indicator the system can produce. It confirms the client is genuinely reactive to self-referential stress — deviation scales with emotional load. Level C items are the primary activation trigger.` })
  } else if (la > lc && la > 0.3) {
    recs.push({ title: 'Elevated Baseline State Detected',
      desc: `T² is highest at Level A (${la.toFixed(2)}), suggesting the client entered the session already in an elevated psychomotor state. Assess pre-session stressors and environmental factors. Flag for session context note.` })
  }

  recs.push({ title: 'Review Hover-Word Hesitation Map',
    desc: "The heatmap identifies specific words within each prompt where the client's cursor paused longest before typing. These micro-hesitations represent sub-verbal, pre-linguistic indicators of emotional activation. Use these as direct interview entry points: ask the client directly about the flagged words." })

  return recs
}

// ── PHQ/GAD gauge ────────────────────────────────────────────────────────────
function ScoreGauge({ label, score, max, thresholds, sublabel }) {
  const pct   = Math.min(100, Math.round((score / max) * 100))
  const color = score >= thresholds[1] ? 'bg-coral' : score >= thresholds[0] ? 'bg-amber' : 'bg-success'
  const tc    = score >= thresholds[1] ? 'text-coral' : score >= thresholds[0] ? 'text-amber' : 'text-success'
  return (
    <div className="card p-5">
      <div className="flex justify-between items-baseline mb-1">
        <p className="text-sm font-semibold text-tmain">{label}</p>
        <p className={`text-2xl font-bold ${tc}`}>{score}<span className="text-sm font-normal text-tsub ml-1">/ {max}</span></p>
      </div>
      <p className={`text-xs font-semibold mb-2 ${tc}`}>{sublabel}</p>
      <div className="h-2 bg-border rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

// ── Metric card ───────────────────────────────────────────────────────────────
function MetricCard({ label, value, interp, color, glossaryKey }) {
  return (
    <div className="card p-5">
      <p className="text-xs text-tsub font-semibold uppercase tracking-wide mb-1 flex items-center gap-1">
        {label}
        {glossaryKey && <InfoTooltip glossaryKey={glossaryKey} />}
      </p>
      <p className={`text-3xl font-bold mb-1 ${color || 'text-tmain'}`}>{value ?? '—'}</p>
      {interp && <p className="text-xs text-tsub leading-relaxed mt-2 border-t border-border/60 pt-2">{interp}</p>}
    </div>
  )
}

// ── Temporal Heatmap (SVG, zoomable + pannable) ───────────────────────────────
function TemporalHeatmap({ snapshots, flag }) {
  const [tooltip,  setTooltip]  = useState(null)
  const [zoom,     setZoom]     = useState(1)
  const [panMs,    setPanMs]    = useState(0)
  const svgRef   = useRef(null)
  const dragRef  = useRef(null)

  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="card p-6">
        <h2 className="font-bold text-tmain text-sm uppercase tracking-wide mb-2">Temporal Hesitation Heatmap</h2>
        <p className="text-tsub text-sm text-center py-10 italic">No significant pause events detected.</p>
      </div>
    )
  }

  const W = 720, H = 320
  const ML = 92, MR = 30, MT = 28, MB = 52
  const plotW = W - ML - MR
  const plotH = H - MT - MB
  const bandH = plotH / 4

  const allPauses = snapshots.map(s => s.pre_typing_pause_ms || 0)
  const xMaxBase  = Math.max(Math.max(...allPauses) * 1.15, 1500)

  const visibleMs  = xMaxBase / zoom
  const clampedPan = Math.max(0, Math.min(panMs, xMaxBase - visibleMs))

  function xPx(ms) { return ML + ((ms - clampedPan) / visibleMs) * plotW }
  function yCy(gid) { return MT + (gid - 0.5) * bandH }

  const tickStep = visibleMs > 8000 ? 2000 : visibleMs > 4000 ? 1000 : visibleMs > 2000 ? 500 : visibleMs > 1000 ? 250 : 100
  const ticks = []
  for (let t = Math.floor(clampedPan / tickStep) * tickStep; t <= clampedPan + visibleMs + tickStep; t += tickStep) ticks.push(t)

  // ── Zoom on wheel ────────────────────────────────────────────────────────────
  const handleWheel = useCallback((e) => {
    e.preventDefault()
    const dir     = e.deltaY < 0 ? 1 : -1
    const newZoom = Math.max(0.5, Math.min(8, zoom * (dir > 0 ? 1.15 : 1 / 1.15)))
    const rect    = svgRef.current.getBoundingClientRect()
    const svgX    = (e.clientX - rect.left) * (W / rect.width)
    const frac    = Math.max(0, Math.min(1, (svgX - ML) / plotW))
    const oldVis  = xMaxBase / zoom
    const newVis  = xMaxBase / newZoom
    const newPan  = clampedPan + frac * (oldVis - newVis)
    setPanMs(Math.max(0, Math.min(newPan, xMaxBase - newVis)))
    setZoom(newZoom)
  }, [zoom, clampedPan, xMaxBase]) // eslint-disable-line

  useEffect(() => {
    const el = svgRef.current
    if (!el) return
    el.addEventListener('wheel', handleWheel, { passive: false })
    return () => el.removeEventListener('wheel', handleWheel)
  }, [handleWheel])

  // ── Drag to pan ──────────────────────────────────────────────────────────────
  function handleMouseDown(e) {
    if (e.button !== 0) return
    dragRef.current = { startX: e.clientX, startPan: clampedPan }
  }
  function handleMouseMove(e) {
    if (!dragRef.current) return
    const rect   = svgRef.current.getBoundingClientRect()
    const dx     = e.clientX - dragRef.current.startX
    const deltaPan = -(dx / rect.width) * W / plotW * visibleMs
    setPanMs(Math.max(0, Math.min(dragRef.current.startPan + deltaPan, xMaxBase - visibleMs)))
  }
  function handleMouseUp()   { dragRef.current = null }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-1">
        <h2 className="font-bold text-tmain text-sm uppercase tracking-wide">Temporal Hesitation Heatmap</h2>
        <div className="flex items-center gap-2">
          <span className="text-xs text-tsub">Scroll to zoom · Drag to pan</span>
          {zoom !== 1 && (
            <button
              onClick={() => { setZoom(1); setPanMs(0) }}
              className="text-xs text-accent font-semibold bg-accent/10 rounded-pill px-3 py-1 hover:bg-accent/20 transition-colors"
            >
              Reset
            </button>
          )}
        </div>
      </div>
      <p className="text-xs text-tsub mb-3">X = reading latency · Y = domain · Node size = latency magnitude · Chips = top hover words</p>
      <div className="overflow-hidden rounded-lg border border-border/50">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          className="w-full"
          style={{ minWidth: 480, cursor: dragRef.current ? 'grabbing' : 'grab', userSelect: 'none' }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={() => { handleMouseUp(); setTooltip(null) }}
        >
          {/* Clip path to keep nodes inside plot area */}
          <defs>
            <clipPath id="hm-clip">
              <rect x={ML} y={MT} width={plotW} height={plotH} />
            </clipPath>
          </defs>

          {/* Domain band backgrounds */}
          {[1, 2, 3, 4].map(gid => (
            <g key={gid}>
              <rect x={ML} y={MT + (gid - 1) * bandH} width={plotW} height={bandH} fill={DOMAIN_BG[gid]} />
              {gid < 4 && (
                <line x1={ML} y1={MT + gid * bandH} x2={W - MR} y2={MT + gid * bandH}
                  stroke="#E4F0F0" strokeDasharray="4,4" />
              )}
              <text x={ML - 6} y={yCy(gid)} textAnchor="end" dominantBaseline="middle"
                fontSize={9} fontWeight="bold" fill={DOMAIN_COLORS[gid]}>
                {DOMAIN_NAMES[gid]}
              </text>
            </g>
          ))}

          {/* Axes */}
          <line x1={ML} y1={MT} x2={ML} y2={H - MB} stroke="#E4F0F0" />
          <line x1={ML} y1={H - MB} x2={W - MR} y2={H - MB} stroke="#E4F0F0" />

          {/* X axis ticks */}
          {ticks.filter(t => xPx(t) >= ML - 1 && xPx(t) <= W - MR + 1).map(t => (
            <g key={t}>
              <line x1={xPx(t)} y1={MT} x2={xPx(t)} y2={H - MB} stroke="#F1F5F9" />
              <line x1={xPx(t)} y1={H - MB} x2={xPx(t)} y2={H - MB + 5} stroke="#E4F0F0" />
              <text x={xPx(t)} y={H - MB + 16} textAnchor="middle" fontSize={8} fill="#7A9A9A">
                {t >= 1000 ? `${(t / 1000).toFixed(1)}s` : `${t}ms`}
              </text>
            </g>
          ))}
          <text x={ML + plotW / 2} y={H - 10} textAnchor="middle" fontSize={9} fill="#7A9A9A">
            Pre-typing pause — time from question shown → first keypress
          </text>

          {/* Nodes (clipped) */}
          <g clipPath="url(#hm-clip)">
            {snapshots.slice(0, 12).map((snap, i) => {
              const gid     = snap.group_id || 1
              const pauseMs = snap.pre_typing_pause_ms || 0
              const cx      = xPx(pauseMs)
              const cy      = yCy(gid)
              const pf      = Math.min(pauseMs / xMaxBase, 1.0)
              const r       = Math.max(12, Math.min(28, Math.round(pf * 18) + 12))
              const col     = DOMAIN_COLORS[gid] || '#888'
              const hover   = snap.hover_words || []
              const topWords = hover.filter(h => (h.word || '').length > 1 && (h.dwell_ms || 0) >= 30).slice(0, 4)
              const chipH   = 20, chipGap = 4
              const totalCH = topWords.length * (chipH + chipGap)

              return (
                <g key={i} style={{ cursor: 'pointer' }}
                  onMouseEnter={(e) => { e.stopPropagation(); setTooltip({ snap, cx, cy }) }}
                  onMouseLeave={(e) => { e.stopPropagation(); setTooltip(null) }}>
                  <circle cx={cx} cy={cy} r={r + 5} fill={col} fillOpacity={0.08} />
                  <circle cx={cx} cy={cy} r={r} fill={col} fillOpacity={0.5} stroke={col} strokeWidth={2} />
                  <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle"
                    fontSize={10} fontWeight="bold" fill={col} style={{ pointerEvents: 'none' }}>
                    {snap.item_id || '?'}
                  </text>
                  {topWords.map((hw, j) => {
                    const word  = hw.word || ''
                    const chipY = cy - r - 12 - totalCH + j * (chipH + chipGap)
                    const chipW = Math.max(50, word.length * 7 + 22)
                    if (chipY < MT - 40) return null
                    return (
                      <g key={j} style={{ pointerEvents: 'none' }}>
                        <rect x={cx - chipW / 2} y={chipY} width={chipW} height={chipH}
                          fill="white" stroke={col} strokeOpacity={j === 0 ? 1 : 0.6} strokeWidth={1.5} rx={5} 
                          className="shadow-sm" />
                        <text x={cx} y={chipY + chipH / 2} textAnchor="middle" dominantBaseline="middle"
                          fontSize={9} fontWeight={j === 0 ? 'bold' : 'medium'}
                          fill={col} fillOpacity={j === 0 ? 1 : 0.8}>
                          {word}
                        </text>
                      </g>
                    )
                  })}
                  {topWords.length > 0 && (
                    <text x={cx} y={cy + r + 15} textAnchor="middle" fontSize={9} fontWeight="bold" fill={col}
                      style={{ pointerEvents: 'none' }}>
                      {Math.round(topWords[0].dwell_ms)}ms
                    </text>
                  )}
                </g>
              )
            })}
          </g>

          {/* Tooltip (outside clip) */}
          {tooltip && (() => {
            const { snap, cx, cy } = tooltip
            const hover      = snap.hover_words || []
            const topWord    = hover[0]
            const totalDwell = hover.reduce((s, h) => s + (h.dwell_ms || 0), 0)
            const lines = [
              `Item: ${snap.item_id || '?'}`,
              `Pause: ${(snap.pre_typing_pause_ms || 0).toFixed(0)} ms`,
              `Top word: ${topWord?.word || '—'}`,
              `Total dwell: ${totalDwell.toFixed(0)} ms`,
              `Hover count: ${topWord?.hover_count || 0}`,
            ]
            const tipW = 168, tipH = lines.length * 15 + 16
            let tx = cx + 16, ty = cy - tipH / 2
            if (tx + tipW > W - MR) tx = cx - tipW - 12
            if (ty < MT) ty = MT + 2
            if (ty + tipH > H - MB) ty = H - MB - tipH - 2
            return (
              <g style={{ pointerEvents: 'none' }}>
                <rect x={tx} y={ty} width={tipW} height={tipH}
                  fill="white" stroke="#E4F0F0" strokeWidth={1} rx={6} />
                {lines.map((line, k) => (
                  <text key={k} x={tx + 10} y={ty + 13 + k * 15} fontSize={9} fill="#0D2D2D">{line}</text>
                ))}
              </g>
            )
          })()}
        </svg>
      </div>
      <div className={`mt-3 rounded-lg px-4 py-2 text-xs font-medium ${flag !== 'GREEN' ? 'bg-coral/10 text-coral' : 'bg-success/10 text-success'}`}>
        {flag !== 'GREEN'
          ? 'Elevated reading latency detected. Larger nodes = longer pre-typing pause. Scroll/drag to explore.'
          : 'Smooth reading trajectories consistent with baseline. No significant hesitation spikes detected.'}
      </div>
    </div>
  )
}

// ── Keystroke Interval Spectrogram (SVG) ─────────────────────────────────────
function Spectrogram({ flightTimes, snapshots, flag, pai }) {
  const [tooltip, setTooltip] = useState(null)

  let times = []
  if (flightTimes && flightTimes.length > 0) {
    times = flightTimes.slice(-14).map(t => t * 1000)
  } else if (snapshots && snapshots.length > 0) {
    times = snapshots.map(s => (s.flight_time || 0) * 1000).filter(t => t > 0)
  }
  if (!times.length) return null

  const W = 720, H = 240
  const ML = 52, MR = 20, MT = 20, MB = 44
  const plotW = W - ML - MR
  const plotH = H - MT - MB
  const isElevated = flag === 'AMBER' || flag === 'RED'
  const color = isElevated ? '#F97316' : '#0ABFBC'

  const mean = times.reduce((a, b) => a + b, 0) / times.length
  const n   = times.length
  const mx  = Math.max(...times)
  const gap = Math.max(4, Math.floor(plotW / Math.max(n * 6, 1)))
  const bw  = Math.max(14, Math.floor((plotW - gap * (n - 1)) / n))
  const totalNeeded = bw * n + gap * (n - 1)
  const startX = ML + Math.floor((plotW - totalNeeded) / 2)

  function barSignal(t) {
    if (t > mean * 2.2) return { label: 'Very slow — possible depressive slowing or distraction', color: '#F27C7C' }
    if (t > mean * 1.5) return { label: 'Slow — mild cognitive load or hesitation', color: '#F5A623' }
    if (t < mean * 0.4) return { label: 'Very fast — possible anxious rush or motor hyperarousal', color: '#F5A623' }
    return { label: 'Normal rhythm for this patient', color: '#36C98E' }
  }

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between mb-1">
        <h2 className="font-bold text-tmain text-sm uppercase tracking-wide flex items-center">
          Keystroke Interval Spectrogram
          <InfoTooltip glossaryKey="Spectrogram" />
        </h2>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${isElevated ? 'bg-amber/15 text-amber' : 'bg-success/15 text-success'}`}>
          Mean: {mean.toFixed(0)} ms
        </span>
      </div>
      <p className="text-xs text-tsub mb-3">Each bar = time between two consecutive keystrokes. Hover a bar to read its clinical signal.</p>
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 400 }}>
          <line x1={ML} y1={MT} x2={ML} y2={H - MB} stroke="#E4F0F0" />
          <line x1={ML} y1={H - MB} x2={W - MR} y2={H - MB} stroke="#E4F0F0" />

          {[0.25, 0.5, 0.75, 1.0].map(frac => {
            const val = mx * frac
            const ty  = H - MB - Math.round(frac * plotH)
            return (
              <g key={frac}>
                <line x1={ML - 4} y1={ty} x2={ML} y2={ty} stroke="#E4F0F0" />
                <line x1={ML} y1={ty} x2={W - MR} y2={ty} stroke="#F8FAFC" />
                <text x={ML - 7} y={ty} textAnchor="end" dominantBaseline="middle"
                  fontSize={7} fill="#7A9A9A">{val.toFixed(0)}</text>
              </g>
            )
          })}

          {/* Mean line */}
          {mx > 0 && (
            <line x1={ML} y1={H - MB - Math.round((mean / mx) * plotH)}
                  x2={W - MR} y2={H - MB - Math.round((mean / mx) * plotH)}
                  stroke="#0ABFBC" strokeDasharray="4 3" strokeOpacity={0.45} />
          )}

          <text x={14} y={MT + plotH / 2} textAnchor="middle" fontSize={9} fill="#7A9A9A"
            transform={`rotate(-90, 14, ${MT + plotH / 2})`}>ms</text>
          <text x={ML + plotW / 2} y={H - 10} textAnchor="middle" fontSize={9} fill="#7A9A9A">
            Keystroke sequence (chronological)
          </text>

          {times.map((t, i) => {
            const sig = barSignal(t)
            const bh = Math.max(4, Math.round(t / mx * plotH))
            const x1 = startX + i * (bw + gap)
            const y1 = H - MB - bh
            return (
              <g key={i} style={{ cursor: 'crosshair' }}
                onMouseEnter={() => setTooltip({ t, x: x1 + bw / 2, y: y1, sig })}
                onMouseLeave={() => setTooltip(null)}>
                <rect x={x1} y={y1} width={bw} height={bh} fill={tooltip?.x === x1 + bw / 2 ? sig.color : color}
                  fillOpacity={tooltip?.x === x1 + bw / 2 ? 1 : 0.8} rx={2} />
                <text x={x1 + bw / 2} y={H - MB + 14} textAnchor="middle" fontSize={7} fill="#7A9A9A">{i + 1}</text>
              </g>
            )
          })}

          {tooltip && (() => {
            const tipW = 210, tipH = 36
            let tx = tooltip.x - tipW / 2, ty = tooltip.y - tipH - 8
            if (tx < ML) tx = ML
            if (tx + tipW > W - MR) tx = W - MR - tipW
            if (ty < MT) ty = tooltip.y + 8
            return (
              <g style={{ pointerEvents: 'none' }}>
                <rect x={tx} y={ty} width={tipW} height={tipH} fill="#0D2D2D" rx={6} />
                <text x={tx + 10} y={ty + 13} fontSize={9} fontWeight="bold" fill="#0ABFBC">{tooltip.t.toFixed(1)} ms</text>
                <text x={tx + 10} y={ty + 26} fontSize={8} fill="rgba(255,255,255,0.75)">{tooltip.sig.label}</text>
              </g>
            )
          })()}
        </svg>
      </div>
      <div className={`mt-3 rounded-xl px-4 py-2.5 text-xs font-medium flex items-start gap-2 ${isElevated ? 'bg-amber/10 text-amber' : 'bg-success/10 text-success'}`}>
        <span className="font-bold shrink-0">{isElevated ? '⚠' : '✓'}</span>
        {isElevated
          ? `Irregular rhythm detected (+${Math.round((pai || 0) * 45)}% above baseline). Tall spikes = pauses where client hesitated — clinical entry points for interview. Consistently short bars = anxious rushing.`
          : 'Rhythm is consistent and within normal range. No clinically significant keystroke irregularity detected.'}
      </div>
    </div>
  )
}

// ── Normative Comparison section ─────────────────────────────────────────────
function NormativeComparison({ metrics, loading }) {
  const hasData = metrics && Object.keys(metrics).length > 0

  const SHOW = ['t2_score', 'psi', 'pai', 'phq_score', 'gad_score']
  const entries = hasData ? SHOW.map(k => metrics[k]).filter(Boolean) : []

  function zColor(z) {
    if (z >= 1.5)  return 'text-coral'
    if (z >= 1.0)  return 'text-amber'
    if (z <= -1.0) return 'text-accent'
    return 'text-success'
  }
  function zInterpret(z, label) {
    const abs = Math.abs(z)
    if (abs < 0.5) return 'Within typical range of the normative population.'
    if (z >= 1.5)  return `Significantly above normative mean — elevated ${label} relative to healthy baseline.`
    if (z >= 1.0)  return `Moderately above normative mean. Some elevation compared to healthy population.`
    if (z <= -1.5) return `Significantly below normative mean.`
    if (z <= -1.0) return `Slightly below normative mean.`
    return 'Within normal range of the normative population.'
  }

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2 mb-1">
        <div className="w-5 h-5 rounded-full bg-[#2D5F5F] flex items-center justify-center flex-shrink-0">
          <span className="text-white text-xs font-bold">N</span>
        </div>
        <h2 className="font-bold text-tmain text-sm uppercase tracking-wide">Population Comparison</h2>
        {hasData && <span className="ml-auto text-xs text-tsub">vs. normative baseline (n={entries[0]?.count ?? '?'})</span>}
      </div>
      <p className="text-xs text-tsub mb-4 leading-relaxed">
        Normative analysis — how this client's scores compare against the study-derived population baseline model
        (n=100 participants). Z-scores show standard deviations from the population mean; percentile shows where
        the client ranks. This complements the ipsative (within-session EWMA) analysis shown above.
      </p>

      {/* Loading state */}
      {loading && (
        <div className="py-8 text-center">
          <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-tsub text-xs">Loading population comparison…</p>
        </div>
      )}

      {/* No data state */}
      {!loading && !hasData && (
        <div className="rounded-xl border border-border/60 bg-[#F7FAFA] px-5 py-6 text-center">
          <p className="text-sm font-semibold text-tsub mb-1">Normative data unavailable for this session</p>
          <p className="text-xs text-tsub/70 leading-relaxed">
            Population comparison requires a completed session with a valid session ID.
            If this is a fresh session, the backend normative model may not have returned data.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {entries.map(m => {
          const pctBar = Math.min(100, Math.max(0, m.pct))
          return (
            <div key={m.label} className="bg-[#F7FAFA] rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold text-tmain flex items-center gap-1">
                  {m.label === 'Hotelling T² Score' ? 'Overall Behavioral Deviation (Hotelling T²)' : m.label}
                  {m.label === 'Hotelling T² Score' && <InfoTooltip glossaryKey="T2" />}
                </p>
                <div className="flex items-center gap-3 text-right">
                  <div>
                    <p className="text-xs text-tsub">Client</p>
                    <p className="font-bold text-tmain text-sm">{Number(m.patient).toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-tsub">Pop. Mean</p>
                    <p className="font-mono text-tsub text-sm">{Number(m.norm_mean).toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-tsub">Z-score</p>
                    <p className={`font-bold text-sm ${zColor(m.z)}`}>{m.z > 0 ? '+' : ''}{m.z}</p>
                  </div>
                  <div>
                    <p className="text-xs text-tsub">Percentile</p>
                    <p className={`font-bold text-sm ${zColor(m.z)}`}>{m.pct.toFixed(0)}th</p>
                  </div>
                </div>
              </div>
              {/* Percentile bar */}
              <div className="relative h-2 bg-border/30 rounded-full overflow-hidden">
                {/* Normal Range Zone (16% to 84%) */}
                <div className="absolute top-0 h-full bg-success/20" style={{ left: '16%', width: '68%' }} />
                <div
                  className={`h-full rounded-full ${m.z >= 1.5 ? 'bg-coral' : m.z >= 1.0 ? 'bg-amber' : m.z <= -1.0 ? 'bg-accent' : 'bg-success'}`}
                  style={{ width: `${pctBar}%` }}
                />
                {/* Midpoint marker */}
                <div className="absolute top-0 left-1/2 w-px h-full bg-white/70 -translate-x-1/2" />
              </div>
              <p className="text-xs text-tsub mt-1.5 leading-relaxed">{zInterpret(m.z, m.label)}</p>
            </div>
          )
        })}
      </div>
      <p className="text-xs text-tsub mt-3 border-t border-border/50 pt-3">
        <strong>Dual-Analytical Approach:</strong> The T² anomaly score above uses ipsative analysis —
        comparing this client's assessment-phase behavior to their own within-session EWMA calibration baseline.
        This table uses normative analysis — comparing against the 100-participant study population model,
        enabling both intra-individual and inter-individual psychomotor interpretation (Thesis §1.3).
      </p>
    </div>
  )
}

// ── Main Report component ─────────────────────────────────────────────────────
export default function Report() {
  const navigate        = useNavigate()
  const { sessionId }   = useParams()
  const { report: ctxReport, setReport } = useApp()

  const [data,        setData]        = useState(null)
  const [normComp,    setNormComp]    = useState(null)
  const [normLoading, setNormLoading] = useState(true)
  const [exporting,   setExporting]   = useState(false)
  const [err,         setErr]         = useState('')
  const [fontScale, setFontScale] = useState(1)

  const FONT_SCALES = [0.85, 1, 1.15, 1.3]
  const scaleIdx = FONT_SCALES.indexOf(fontScale) === -1 ? 1 : FONT_SCALES.indexOf(fontScale)
  function decreaseFont() { if (scaleIdx > 0) setFontScale(FONT_SCALES[scaleIdx - 1]) }
  function increaseFont() { if (scaleIdx < FONT_SCALES.length - 1) setFontScale(FONT_SCALES[scaleIdx + 1]) }

  useEffect(() => {
    if (sessionId) {
      // Revisiting a saved session — load detail and normative compare
      api.sessionDetail(sessionId).then(d => {
        if (d.error) { setErr(d.error); return }
        setData(d)
      })
      setNormLoading(true)
      api.normativeCompare(sessionId).then(d => {
        const metrics = d?.available ? d.metrics       // {available, metrics} wrapper
                      : (d?.t2_score || d?.psi) ? d   // backend returned dict directly
                      : null
        if (metrics) setNormComp(metrics)
        setNormLoading(false)
      }).catch(() => setNormLoading(false))
    } else if (ctxReport) {
      setData(ctxReport)
      const freshSid = ctxReport?.session_id
      if (freshSid) {
        setNormLoading(true)
        api.normativeCompare(freshSid).then(d => {
          const metrics = d?.available ? d.metrics
                        : (d?.t2_score || d?.psi) ? d
                        : null
          if (metrics) setNormComp(metrics)
          setNormLoading(false)
        }).catch(() => setNormLoading(false))
      } else {
        setNormLoading(false)
      }
    }
  }, [sessionId, ctxReport])

  async function handleExport() {
    if (!data) return
    setExporting(true)
    const res = await api.exportReport(data)
    setExporting(false)
    if (res.success && res.file) {
      window.electron?.openExternal?.(`file:///${res.file.replace(/\\/g, '/')}`)
    } else {
      alert(res.error || 'Export failed.')
    }
  }

  if (err) return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 flex items-center justify-center">
        <p className="text-coral">{err}</p>
      </main>
    </div>
  )

  if (!data) return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-tsub text-sm">Loading report…</p>
        </div>
      </main>
    </div>
  )

  const { student_id, timestamp, phq, gad, analysis, visuals } = data
  const flag      = analysis?.flag  || 'GREEN'
  const fs        = FLAG_STYLE[flag] || FLAG_STYLE.GREEN
  const FlagIcon  = fs.icon
  const snapshots = visuals?.question_snapshots || []
  const domainT2  = visuals?.domain_t2  || {}
  const levelT2   = visuals?.level_t2   || {}
  const flights   = visuals?.flight_times || []

  const t2    = analysis?.t2_score    ?? 0
  const thr   = analysis?.t2_threshold ?? 0
  const psi   = analysis?.psi ?? 0
  const pai   = analysis?.pai ?? 0
  const t2Color = (thr && t2 > thr) ? 'text-coral' : 'text-success'

  const phqScore = phq?.score ?? 0
  const gadScore = gad?.score ?? 0
  const recLabel = analysis?.label || ''

  // Domain bar chart data
  const domainData = Object.entries(domainT2).map(([gid, val]) => ({
    name:  DOMAIN_NAMES[Number(gid)] || `G${gid}`,
    value: Number(Number(val).toFixed(3)),
    color: DOMAIN_COLORS[Number(gid)] || '#888',
    gid:   Number(gid),
  })).sort((a, b) => a.gid - b.gid)

  // Level bar chart data
  const levelData = Object.entries(levelT2).map(([lv, val]) => ({
    name:  `Level ${lv}`,
    value: Number(Number(val).toFixed(3)),
    color: LEVEL_COLORS[lv] || '#888',
  }))

  // Flight time histogram (bucketed, legacy chart kept)
  const histData = (() => {
    if (!flights.length) return []
    const buckets = {}
    flights.forEach(f => {
      const b = Math.round(f * 20) / 20
      buckets[b] = (buckets[b] || 0) + 1
    })
    return Object.entries(buckets)
      .sort(([a], [b]) => Number(a) - Number(b))
      .slice(0, 20)
      .map(([ms, count]) => ({ ms: `${Math.round(Number(ms) * 1000)}ms`, count }))
  })()

  const recs = clinicalRecs(flag, recLabel, psi, pai, phqScore, gadScore, domainT2, levelT2)

  return (
    <div className="h-screen flex bg-bg" style={{ position: 'relative' }}>
      <AnimatedBackground variant="subtle" />
      <Sidebar />
      <main className="flex-1 overflow-y-auto px-10 py-8 animate-fade-in" style={{ position: 'relative', zIndex: 1 }}>

        {/* Top bar */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => { setReport(null); navigate(sessionId ? `/clients/${student_id}` : '/dashboard') }}
            className="flex items-center gap-2 text-tsub hover:text-tmain text-sm transition-colors"
          >
            <ArrowLeft size={16} /> Back
          </button>
          <div className="flex items-center gap-2">
            {/* Font size controls */}
            <div className="flex items-center gap-1 bg-white border border-border rounded-xl px-1.5 py-1 shadow-card">
              <button
                onClick={decreaseFont}
                disabled={scaleIdx === 0}
                title="Decrease text size"
                className="w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold text-tsub hover:bg-bg hover:text-tmain transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                A−
              </button>
              <span className="text-xs text-tsub px-1 select-none w-8 text-center font-semibold">
                {Math.round(fontScale * 100)}%
              </span>
              <button
                onClick={increaseFont}
                disabled={scaleIdx === FONT_SCALES.length - 1}
                title="Increase text size"
                className="w-7 h-7 rounded-lg flex items-center justify-center text-base font-bold text-tsub hover:bg-bg hover:text-tmain transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                A+
              </button>
            </div>
            <button
              onClick={handleExport}
              disabled={exporting}
              className="btn-primary flex items-center gap-2 text-sm h-9 px-4"
            >
              <Download size={14} />
              {exporting ? 'Exporting…' : 'Export Full Report'}
            </button>
          </div>
        </div>

        <div style={{ zoom: fontScale }}>
        {/* Title */}
        <h1 className="text-2xl font-bold text-tmain mb-0.5">Clinical Assessment Report</h1>
        <p className="text-tsub text-sm mb-6">
          Client: <span className="font-semibold text-tmain">{student_id}</span>
          <span className="mx-2 text-border">·</span>
          {timestamp ? new Date(String(timestamp).replace(' ', 'T') + 'Z').toLocaleString() : '—'}
        </p>

        <div className="w-full space-y-4">

          {/* Status banner */}
          <div className={`rounded-card border p-4 flex items-center gap-4 ${fs.bg}`}>
            <FlagIcon size={24} className={fs.text} />
            <div>
              <p className={`font-bold text-base ${fs.text} flex items-center gap-1`}>
                {fs.label}<InfoTooltip glossaryKey="Flag" />
              </p>
              {analysis?.label && <p className="text-sm text-tsub mt-0.5">{analysis.label}</p>}
            </div>
            {analysis?.confidence != null && (
              <div className="ml-auto text-right">
                <p className="text-xs text-tsub">Confidence</p>
                <p className={`font-bold text-xl ${fs.text}`}>{Math.round(analysis.confidence * 100)}%</p>
              </div>
            )}
          </div>

          {/* Top row: PHQ/GAD + Biometric metrics */}
          <div className="grid grid-cols-5 gap-4">
            <div className="col-span-2 grid grid-rows-2 gap-4">
              <ScoreGauge label="PHQ-9 — Depression"  score={phqScore} max={27} thresholds={[10, 15]} sublabel={phqLabel(phqScore)} />
              <ScoreGauge label="GAD-7 — Anxiety"     score={gadScore} max={21} thresholds={[10, 15]} sublabel={gadLabel(gadScore)} />
            </div>
            <MetricCard
              label="Hotelling T² Score"
              value={t2.toFixed(3)}
              color={t2Color}
              interp={t2Interp(t2, thr)}
              glossaryKey="T2"
            />
            <MetricCard
              label="Psychomotor Slowing Index (PSI)"
              value={psi.toFixed(3)}
              color={(() => {
                const nz = normComp?.psi?.z
                if (nz !== undefined) return nz > 2 ? 'text-coral' : nz > 1 ? 'text-amber' : nz < -1 ? 'text-accent' : 'text-success'
                return psi >= 2 ? 'text-coral' : psi >= 0.5 ? 'text-amber' : 'text-success'
              })()}
              interp={psiInterp(psi, normComp?.psi?.z)}
              glossaryKey="PSI"
            />
            <MetricCard
              label="Psychomotor Agitation Index (PAI)"
              value={pai.toFixed(3)}
              color={(() => {
                const nz = normComp?.pai?.z
                if (nz !== undefined) return nz > 2 ? 'text-coral' : nz > 1 ? 'text-amber' : nz < -1 ? 'text-accent' : 'text-success'
                return pai >= 2 ? 'text-coral' : pai >= 0.5 ? 'text-amber' : 'text-success'
              })()}
              interp={paiInterp(pai, normComp?.pai?.z)}
              glossaryKey="PAI"
            />
          </div>

          {/* Heatmap + Spectrogram side by side */}
          <div className="grid grid-cols-2 gap-4">
            <TemporalHeatmap snapshots={snapshots} flag={flag} />
            <Spectrogram flightTimes={flights} snapshots={snapshots} flag={flag} pai={pai} />
          </div>

          {/* Domain T² + Level + Flight in one responsive row */}
          {(domainData.length > 0 || levelData.length > 0 || histData.length > 0) && (
          <div className="grid grid-cols-2 gap-4">
          {domainData.length > 0 && (
            <div className="card p-5">
              <h2 className="font-bold text-tmain text-sm uppercase tracking-wide mb-1 flex items-center">
                Domain T² Scores<InfoTooltip glossaryKey="DomainT2" />
              </h2>
              <p className="text-xs text-tsub mb-3">Hover each bar to see what a spike in that domain clinically suggests.</p>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={domainData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#7A9A9A' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#7A9A9A' }} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const d = payload[0].payload
                      const tips = {
                        1: 'Burnout, perfectionism, task-overload schema. Screen for occupational stress and Type-A patterns.',
                        2: 'Attachment disruption, rejection sensitivity. Consider IIP-32 for interpersonal profiling.',
                        3: 'Performance anxiety, impostor syndrome. Consider LSAS if social anxiety is suspected.',
                        4: 'Core negative beliefs about self. Highest suicide-risk correlation — assess directly. Consider DAS-24.',
                      }
                      return (
                        <div className="rounded-xl p-3 shadow-xl text-xs" style={{ background: '#0D2D2D', border: '1px solid rgba(10,191,188,0.3)', maxWidth: 240 }}>
                          <p className="font-bold mb-1" style={{ color: d.color }}>{d.name}</p>
                          <p className="text-white/90 mb-1">T² = <strong>{d.value}</strong>{thr > 0 ? ` (threshold: ${thr.toFixed(3)})` : ''}</p>
                          <p className="text-white/65 leading-snug">{tips[d.gid]}</p>
                        </div>
                      )
                    }}
                  />
                  {thr > 0 && <ReferenceLine y={thr} stroke="#F27C7C" strokeDasharray="4 2" label={{ value: 'Threshold', position: 'insideTopRight', fontSize: 10, fill: '#F27C7C' }} />}
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {domainData.map((d, i) => <Cell key={i} fill={d.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="flex gap-3 mt-2 flex-wrap">
                {domainData.map(d => (
                  <div key={d.gid} className="flex items-center gap-1 text-xs text-tsub">
                    <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: d.color }} />
                    {d.name}: <span className="font-bold text-tmain">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Level T² + Flight stacked in right column */}
          <div className="space-y-4">
            {levelData.length > 0 && (
              <div className="card p-5">
                <h2 className="font-bold text-tmain text-sm uppercase tracking-wide mb-1 flex items-center">
                  T² by Emotional Load Level<InfoTooltip glossaryKey="LevelABC" />
                </h2>
                <p className="text-xs text-tsub mb-3">Hover each bar to read what that load level's pattern means.</p>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={levelData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#7A9A9A' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#7A9A9A' }} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null
                        const d = payload[0].payload
                        const lv = d.name.split(' ').pop()
                        const interps = {
                          A: 'Lowest stress level. If T² is already high here, the patient entered the session in a pre-activated state — assess pre-session stressors.',
                          B: 'Moderate stress. Rising T² from A→B confirms emotional reactivity is building.',
                          C: 'Highest stress level. Peak T² here = genuine dose-response — strongest clinical validity signal.',
                        }
                        return (
                          <div className="rounded-xl p-3 shadow-xl text-xs" style={{ background: '#0D2D2D', border: '1px solid rgba(10,191,188,0.3)', maxWidth: 220 }}>
                            <p className="font-bold mb-1" style={{ color: d.color }}>{d.name}</p>
                            <p className="text-white/90 mb-1">T² = <strong>{d.value}</strong></p>
                            <p className="text-white/65 leading-snug">{interps[lv]}</p>
                          </div>
                        )
                      }}
                    />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {levelData.map((d, i) => <Cell key={i} fill={d.color} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="flex gap-4 mt-2">
                  <span className="flex items-center gap-1 text-xs text-tsub"><span className="w-2.5 h-2.5 rounded-sm inline-block bg-success" />A: Low load</span>
                  <span className="flex items-center gap-1 text-xs text-tsub"><span className="w-2.5 h-2.5 rounded-sm inline-block bg-amber" />B: Moderate</span>
                  <span className="flex items-center gap-1 text-xs text-tsub"><span className="w-2.5 h-2.5 rounded-sm inline-block bg-coral" />C: High load</span>
                </div>
              </div>
            )}

            {histData.length > 0 && (
              <div className="card p-5">
                <h2 className="font-bold text-tmain text-sm uppercase tracking-wide mb-1">Keystroke Flight Time Distribution</h2>
                <p className="text-xs text-tsub mb-3">Hover a bar to see what that timing bucket indicates clinically.</p>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={histData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                    <XAxis dataKey="ms" tick={{ fontSize: 10, fill: '#7A9A9A' }} interval={2} />
                    <YAxis tick={{ fontSize: 11, fill: '#7A9A9A' }} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null
                        const d = payload[0].payload
                        const ms = parseInt(d.ms)
                        let signal = ms < 80
                          ? 'Very short — anxious rushing or automatic motor response'
                          : ms < 160 ? 'Fast-normal — efficient typing, low cognitive load'
                          : ms < 280 ? 'Normal range — consistent with calm, focused state'
                          : ms < 450 ? 'Slightly slow — mild hesitation or processing pause'
                          : 'Prolonged — psychomotor slowing or cognitive disruption'
                        return (
                          <div className="rounded-xl p-3 shadow-xl text-xs" style={{ background: '#0D2D2D', border: '1px solid rgba(10,191,188,0.3)', maxWidth: 200 }}>
                            <p className="font-bold text-accent mb-1">{d.ms} bucket</p>
                            <p className="text-white/90 mb-1">{d.count} keystrokes</p>
                            <p className="text-white/65 leading-snug">{signal}</p>
                          </div>
                        )
                      }}
                    />
                    <Bar dataKey="count" fill="#0ABFBC" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-xs text-tsub mt-2">Inter-keystroke interval frequency · {flights.length} samples</p>
              </div>
            )}
          </div>
          </div>
          )}

          {/* Clinical Rationale */}
          {analysis?.rationale && (
            <div className="card p-6">
              <div className="flex items-center gap-2 mb-3">
                <Info size={16} className="text-accent" />
                <h2 className="font-bold text-tmain text-sm uppercase tracking-wide">Clinical Rationale</h2>
              </div>
              <p className="text-tmain text-sm leading-relaxed">{analysis.rationale}</p>
            </div>
          )}

          {/* Clinical Recommendations */}
          {recs.length > 0 && (
            <div>
              <h2 className="font-bold text-tmain text-sm uppercase tracking-wide mb-3 px-1">Clinical Recommendations</h2>
              <div className="grid grid-cols-2 gap-4">
                {recs.map((rec, i) => (
                  <div key={i} className="card p-5 flex gap-4">
                    <div className="flex-shrink-0 w-7 h-7 rounded-full bg-accent flex items-center justify-center">
                      <span className="text-white text-xs font-bold">{i + 1}</span>
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-tmain leading-snug mb-1">{rec.title}</p>
                      <p className="text-xs text-tsub leading-relaxed">{rec.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Population Comparison (normative) */}
          <NormativeComparison metrics={normComp} loading={normLoading} />

          {/* Per-question biometric table */}
          {snapshots.length > 0 && (() => {
            const flagged  = snapshots.filter(s => s.flag === 'RED' || s.flag === 'AMBER')
            const redItems = snapshots.filter(s => s.flag === 'RED').map(s => s.item_id).join(', ')
            const ambItems = snapshots.filter(s => s.flag === 'AMBER').map(s => s.item_id).join(', ')
            const maxT2Snap = snapshots.reduce((best, s) => (s.t2_score || 0) > (best.t2_score || 0) ? s : best, snapshots[0])
            const maxPauseSnap = snapshots.reduce((best, s) => (s.pre_typing_pause_ms || 0) > (best.pre_typing_pause_ms || 0) ? s : best, snapshots[0])
            const allHovers = snapshots.flatMap(s => s.hover_words || [])
            const globalTop = allHovers.sort((a, b) => (b.dwell_ms || 0) - (a.dwell_ms || 0))[0]
            const topWord   = globalTop?.word

            return (
              <div className="card overflow-hidden">
                <div className="px-6 py-4 border-b border-border">
                  <h2 className="font-bold text-tmain text-sm uppercase tracking-wide mb-0.5">Per-Question Biometric Breakdown</h2>
                  <p className="text-tsub text-xs">Biometric features recorded for each prompt. Rows with elevated T² indicate psychomotor deviation from baseline.</p>
                </div>

                {/* Summary interpretation bar */}
                <div className="px-6 py-4 bg-[#F7FAFA] border-b border-border/50 grid grid-cols-3 gap-4 text-xs">
                  <div>
                    <p className="font-semibold text-tsub uppercase tracking-wide mb-1">Flagged Items</p>
                    {flagged.length === 0 ? (
                      <p className="text-success font-medium">All items within normal range</p>
                    ) : (
                      <div className="space-y-0.5">
                        {redItems  && <p className="text-coral font-medium">RED: {redItems}</p>}
                        {ambItems  && <p className="text-amber font-medium">AMBER: {ambItems}</p>}
                        <p className="text-tsub mt-1">{flagged.length} of {snapshots.length} items elevated</p>
                      </div>
                    )}
                  </div>
                  <div>
                    <p className="font-semibold text-tsub uppercase tracking-wide mb-1">Peak T² Item</p>
                    <p className="text-tmain font-bold">{maxT2Snap?.item_id || '—'} <span className="font-normal text-tsub">({Number(maxT2Snap?.t2_score || 0).toFixed(3)})</span></p>
                    <p className="text-tsub mt-0.5 leading-relaxed">{maxT2Snap?.group_name?.split(':')[1]?.trim() || '—'}, Level {maxT2Snap?.level || '—'}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-tsub uppercase tracking-wide mb-1">Reading Latency Peak</p>
                    <p className="text-tmain font-bold">{maxPauseSnap?.item_id || '—'} <span className="font-normal text-tsub">({Math.round(maxPauseSnap?.pre_typing_pause_ms || 0)} ms)</span></p>
                    {topWord && <p className="text-tsub mt-0.5">Top hover word: <span className="font-semibold text-tmain">&ldquo;{topWord}&rdquo;</span></p>}
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-[#F7FAFA] text-tsub font-semibold uppercase tracking-wide">
                        {['ID', 'Domain', 'Lvl', 'T²', 'PSI', 'PAI', 'Flight (ms)', 'Pause (ms)', 'Top Hover Word', 'Flag', 'Interpretation'].map(h => (
                          <th key={h} className="px-4 py-3 text-left whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {snapshots.map((snap, i) => {
                        const lv     = snap.level || 'A'
                        const lc     = { A: 'text-success', B: 'text-amber', C: 'text-coral' }[lv] || 'text-tsub'
                        const fc     = snap.flag === 'RED' ? 'text-coral' : snap.flag === 'AMBER' ? 'text-amber' : 'text-success'
                        const fcBg   = snap.flag === 'RED' ? 'bg-coral/15' : snap.flag === 'AMBER' ? 'bg-amber/15' : 'bg-success/15'
                        const psi_v  = Number(snap.psi || 0)
                        const pai_v  = Number(snap.pai || 0)
                        const topHW  = (snap.hover_words || [])[0]

                        // Per-row interpretation
                        let interp = ''
                        if (snap.flag === 'RED') {
                          interp = psi_v > pai_v * 1.2
                            ? 'Significant slowing — motor inhibition pattern'
                            : pai_v > psi_v * 1.2
                            ? 'Significant agitation — cursor irregularity elevated'
                            : 'Significant deviation — mixed psychomotor signal'
                        } else if (snap.flag === 'AMBER') {
                          interp = `Moderate elevation on ${lv === 'C' ? 'highest-load' : lv === 'B' ? 'moderate-load' : 'low-load'} item`
                        } else {
                          interp = 'Within normal psychomotor range'
                        }

                        return (
                          <tr key={i} className={`border-t border-border/50 ${i % 2 === 1 ? 'bg-[#FAFCFC]' : ''}`}>
                            <td className="px-4 py-2.5 font-bold text-tmain">{snap.item_id || '—'}</td>
                            <td className="px-4 py-2.5 text-tsub max-w-[110px] truncate">{snap.group_name?.split(':')[1]?.trim() || '—'}</td>
                            <td className={`px-4 py-2.5 font-bold ${lc}`}>{lv}</td>
                            <td className="px-4 py-2.5 font-mono">{Number(snap.t2_score || 0).toFixed(3)}</td>
                            <td className={`px-4 py-2.5 font-mono ${psi_v >= 2 ? 'text-coral' : psi_v >= 0.5 ? 'text-amber' : 'text-tsub'}`}>{psi_v.toFixed(3)}</td>
                            <td className={`px-4 py-2.5 font-mono ${pai_v >= 2 ? 'text-coral' : pai_v >= 0.5 ? 'text-amber' : 'text-tsub'}`}>{pai_v.toFixed(3)}</td>
                            <td className="px-4 py-2.5 font-mono text-tsub">{Math.round((snap.flight_time || 0) * 1000)}</td>
                            <td className="px-4 py-2.5 font-mono text-tsub">{Math.round(snap.pre_typing_pause_ms || 0)}</td>
                            <td className="px-4 py-2.5 text-tmain max-w-[90px] truncate">
                              {topHW ? <span className="font-medium">&ldquo;{topHW.word}&rdquo;</span> : <span className="text-tsub">—</span>}
                            </td>
                            <td className="px-4 py-2.5">
                              <span className={`px-2 py-0.5 rounded-full font-bold ${fcBg} ${fc}`}>
                                {snap.flag || 'GREEN'}
                              </span>
                            </td>
                            <td className={`px-4 py-2.5 max-w-[200px] ${snap.flag === 'RED' ? 'text-coral' : snap.flag === 'AMBER' ? 'text-amber' : 'text-tsub'}`}>
                              {interp}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          })()}

        </div>
        </div>{/* end zoom wrapper */}
      </main>
    </div>
  )
}
