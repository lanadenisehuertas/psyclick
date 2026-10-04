import { useEffect, useState, useRef, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Download, AlertTriangle, Info, Activity, Users, ListChecks } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'
import { motion, MotionConfig } from 'motion/react'
import Sidebar from '../components/Sidebar.jsx'
import { StatusHero, Section, Collapsible, ScaleBar, ResultCard } from '../components/ReportParts.jsx'
import { formatTimestamp } from '../lib/status.jsx'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'

// ── Clinical glossary ─────────────────────────────────────────────────────────
const GLOSSARY = {
  T2: {
    title: "Hotelling T² Score",
    what: "How much the patient's typing + mouse behavior shifted from their own baseline today.",
    flag: "Threshold = the 95th percentile of this score among 83 healthy normative testers, so about 1 in 20 healthy people exceed it. Above the 99th percentile with a severe fuzzy pattern = RED.",
    how: "Multivariate distance from the patient's own calibration baseline: T² = Δxᵀ·S⁻¹·Δx (ipsative). Cut-offs are Harrell-Davis estimates from the healthy tester population.",
  },
  PSI: {
    title: "Psychomotor Slowing Index (PSI)",
    what: "Composite index of motor slowing — elevated flight time, dwell time, and pause frequency relative to the client's own EWMA calibration baseline. Operationalizes psychomotor retardation (depression-linked inhibition).",
    flag: "Read against healthy testers: above the 85th percentile = moderate, above the 95th = marked slowing. PSI accumulates even in healthy people across the prompts, so raw size alone is not a signal. Pools feature contributions from flight time, dwell time, and pause frequency (Thesis §1.2).",
    how: "Cᵢ = (xᵢ − μᵢ) × [S⁻¹ · (x − μ)]ᵢ summed over PSI features (flight_time, dwell_time, pause_frequency) where diff > 0 (Mason & Young, 2002).",
  },
  PAI: {
    title: "Psychomotor Agitation Index (PAI)",
    what: "Composite index of motor agitation — elevated path entropy, cursor jerk, error rate, and cursor velocity relative to the client's own EWMA calibration baseline. Operationalizes psychomotor agitation (anxiety-linked erratic movement).",
    flag: "Read against healthy testers: above the 85th percentile = moderate, above the 95th = marked agitation. PAI accumulates even in healthy people across the prompts, so raw size alone is not a signal. Pools feature contributions from path entropy, jerk, error rate, cursor velocity, and typing velocity (Thesis §1.2).",
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
        className="ml-1 text-tsub/60 hover:text-accent-ink transition-colors focus:outline-none"
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
            <p className="font-bold text-[13px] text-accent-ink">{entry.title}</p>
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
const DOMAIN_NAMES  = { 1: 'Time & workload', 2: 'Relationships', 3: 'Performance', 4: 'Self-image' }
const DOMAIN_COLORS = { 1: '#5BA4CF', 2: '#0ABFBC', 3: '#36C98E', 4: '#F27C7C' }
const DOMAIN_BG     = { 1: '#EFF6FF', 2: '#E0FAFA', 3: '#ECFDF5', 4: '#FFF0F0' }
const LEVEL_NAMES   = { A: 'Mild prompts', B: 'Moderate prompts', C: 'Strong prompts' }
const DOMAIN_TIPS   = {
  1: 'Burnout, perfectionism, task overload. Screen for occupational stress.',
  2: 'Attachment disruption, rejection sensitivity. Consider IIP-32 for interpersonal profiling.',
  3: 'Performance anxiety, impostor feelings. Consider LSAS if social anxiety is suspected.',
  4: 'Core negative beliefs about self. Highest suicide-risk correlation — assess directly. Consider DAS-24.',
}
const LEVEL_TIPS    = {
  A: 'Mildest prompts. A high value here suggests the client arrived already activated — ask about pre-session stressors.',
  B: 'Moderate prompts. A rise from mild to moderate shows reactivity is building.',
  C: 'Strongest prompts. The highest value here is the clearest sign of a genuine reaction to emotional load.',
}

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

// Healthy reference values (p75 / p95) used when no percentile is available
const HEALTHY_REF = { psi: { p75: 9.32, p95: 29.63 }, pai: { p75: 15.55, p95: 80.26 } }

// ── Clinical recommendations (ported from Python _clinical_recs) ─────────────
function clinicalRecs(flag, label = '', psi = 0, pai = 0, phq = 0, gad = 0, domainT2 = {}, levelT2 = {}, itemP95 = Infinity) {
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

  // Pattern-specific advice only when the session itself was flagged
  const flagged = flag === 'RED' || flag === 'AMBER'
  if (!flagged) {
    // no psychomotor pattern advice for a typical session
  } else if (label.includes('Retardation') || psi > pai * 1.3) {
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
    if (Number(peakVal) > itemP95) {
      recs.push({ title: `Peak Domain: ${names[Number(peakGid)] || '?'} (T²=${Number(peakVal).toFixed(1)})`,
        desc: `This domain produced the highest psychomotor deviation in the session. ${tips[Number(peakGid)] || ''}` })
    }
  }

  const la = levelT2.A || 0, lb = levelT2.B || 0, lc = levelT2.C || 0
  if (lc > lb && lb > la && lc > itemP95) {
    recs.push({ title: 'Dose-Response Escalation — High Clinical Validity',
      desc: `T² increases monotonically A→B→C (A=${la.toFixed(2)}, B=${lb.toFixed(2)}, C=${lc.toFixed(2)}). This is the strongest internal validity indicator the system can produce. It confirms the client is genuinely reactive to self-referential stress — deviation scales with emotional load. Level C items are the primary activation trigger.` })
  } else if (la > lc && la > itemP95) {
    recs.push({ title: 'Elevated Baseline State Detected',
      desc: `T² is highest at Level A (${la.toFixed(2)}), suggesting the client entered the session already in an elevated psychomotor state. Assess pre-session stressors and environmental factors. Flag for session context note.` })
  }

  recs.push({ title: 'Review Hover-Word Hesitation Map',
    desc: "The heatmap identifies specific words within each prompt where the client's cursor paused longest before typing. These micro-hesitations represent sub-verbal, pre-linguistic indicators of emotional activation. Use these as direct interview entry points: ask the client directly about the flagged words." })

  return recs
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
              className="text-xs text-accent-ink font-semibold bg-accent/10 rounded-pill px-3 py-1 hover:bg-accent/20 transition-colors"
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
      <div className={`mt-3 rounded-lg px-4 py-2 text-xs font-medium ${flag !== 'GREEN' ? 'bg-coral/10 text-coral-ink' : 'bg-success/10 text-success-ink'}`}>
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
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${isElevated ? 'bg-amber/15 text-amber-ink' : 'bg-success/15 text-success-ink'}`}>
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
      <div className={`mt-3 rounded-xl px-4 py-2.5 text-xs font-medium flex items-start gap-2 ${isElevated ? 'bg-amber/10 text-amber-ink' : 'bg-success/10 text-success-ink'}`}>
        <span className="font-bold shrink-0">{isElevated ? '⚠' : '✓'}</span>
        {isElevated
          ? `Irregular rhythm detected (+${Math.round((pai || 0) * 45)}% above baseline). Tall spikes = pauses where client hesitated — clinical entry points for interview. Consistently short bars = anxious rushing.`
          : 'Rhythm is consistent and within normal range. No clinically significant keystroke irregularity detected.'}
      </div>
    </div>
  )
}

// ── Normative Comparison section ─────────────────────────────────────────────
// ── Population comparison (specialist detail) ───────────────────────────────
const NORM_LABELS = {
  t2_score:  { name: 'Overall behaviour change', tech: 'Hotelling T²' },
  psi:       { name: 'Slowing',                  tech: 'Psychomotor Slowing Index (PSI)' },
  pai:       { name: 'Restlessness',             tech: 'Psychomotor Agitation Index (PAI)' },
  phq_score: { name: 'Depression questionnaire', tech: 'PHQ-9' },
  gad_score: { name: 'Anxiety questionnaire',    tech: 'GAD-7' },
}

function percentileValue(pct) {
  return pct >= 99.5 ? '99+' : String(Math.round(pct))
}

function percentileText(pct) {
  if (pct === undefined || pct === null) return ''
  if (pct >= 99.5) return 'Higher than almost all healthy adults'
  if (pct < 1) return 'Lower than almost all healthy adults'
  if (pct < 85) return `Typical — higher than ${Math.round(pct)}% of healthy adults`
  return `Higher than ${Math.round(pct)}% of healthy adults`
}

function NormativeComparison({ metrics, loading }) {
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

function QuestionBreakdown({ snapshots, itemP95 }) {
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

// ── Main Report component ─────────────────────────────────────────────────────
const FALLBACK_THRESHOLDS = { session: { p95: 77.8, p99: 114.1 }, item: { p95: 526.4, p99: 932.9 } }

export default function Report() {
  const navigate        = useNavigate()
  const { sessionId }   = useParams()
  const { report: ctxReport, setReport } = useApp()

  const [data,        setData]        = useState(null)
  const [normComp,    setNormComp]    = useState(null)
  const [normLoading, setNormLoading] = useState(true)
  const [thresholds,  setThresholds]  = useState(FALLBACK_THRESHOLDS)
  const [exporting,   setExporting]   = useState(false)
  const [exportMsg,   setExportMsg]   = useState('')
  const [err,         setErr]         = useState('')
  const [fontScale, setFontScale] = useState(1)

  const FONT_SCALES = [0.85, 1, 1.15, 1.3]
  const scaleIdx = FONT_SCALES.indexOf(fontScale) === -1 ? 1 : FONT_SCALES.indexOf(fontScale)
  function decreaseFont() { if (scaleIdx > 0) setFontScale(FONT_SCALES[scaleIdx - 1]) }
  function increaseFont() { if (scaleIdx < FONT_SCALES.length - 1) setFontScale(FONT_SCALES[scaleIdx + 1]) }

  useEffect(() => {
    api.normativeStats().then(d => { if (d?.thresholds?.session) setThresholds(d.thresholds) }).catch(() => {})
  }, [])

  useEffect(() => {
    function loadCompare(sid) {
      setNormLoading(true)
      api.normativeCompare(sid).then(d => {
        const metrics = d?.available ? d.metrics
                      : (d?.t2_score || d?.psi) ? d
                      : null
        if (metrics) setNormComp(metrics)
        setNormLoading(false)
      }).catch(() => setNormLoading(false))
    }
    if (sessionId) {
      // Revisiting a saved session — load detail and normative compare
      api.sessionDetail(sessionId).then(d => {
        if (d.error) { setErr(d.error); return }
        setData(d)
      })
      loadCompare(sessionId)
    } else if (ctxReport) {
      setData(ctxReport)
      if (ctxReport?.session_id) loadCompare(ctxReport.session_id)
      else setNormLoading(false)
    }
  }, [sessionId, ctxReport])

  async function handleExport() {
    if (!data) return
    setExporting(true)
    setExportMsg('')
    const res = await api.exportReport(data)
    setExporting(false)
    if (res.success && res.file) {
      setExportMsg('Encrypted report saved.')
      window.electron?.openExternal?.(`file:///${res.file.replace(/\\/g, '/')}`)
    } else {
      setExportMsg(res.error || 'Export failed. Please try again.')
    }
  }

  if (err) return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 flex items-center justify-center p-8">
        <div className="card p-8 max-w-md text-center" role="alert">
          <AlertTriangle size={28} className="text-coral-ink mx-auto mb-3" aria-hidden="true" />
          <p className="font-semibold text-tmain mb-1">This report could not be opened</p>
          <p className="text-sm text-tsub mb-5">{err}</p>
          <button onClick={() => navigate('/clients')} className="btn-primary">Back to clients</button>
        </div>
      </main>
    </div>
  )

  if (!data) return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center" role="status">
          <div className="w-10 h-10 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-tsub">Loading report…</p>
        </div>
      </main>
    </div>
  )

  const { student_id, timestamp, phq, gad, analysis, visuals } = data
  const flag      = analysis?.flag  || 'GREEN'
  const snapshots = visuals?.question_snapshots || []
  const domainT2  = visuals?.domain_t2  || {}
  const levelT2   = visuals?.level_t2   || {}
  const flights   = visuals?.flight_times || []

  const t2    = analysis?.t2_score    ?? 0
  const thr   = analysis?.t2_threshold ?? 0
  const psi   = analysis?.psi ?? 0
  const pai   = analysis?.pai ?? 0
  const insufficient = analysis?.label === 'Insufficient Data'

  const phqScore = phq?.score ?? 0
  const gadScore = gad?.score ?? 0
  const recLabel = analysis?.label || ''

  const sP95 = thresholds.session.p95, sP99 = thresholds.session.p99
  const iP95 = thresholds.item.p95
  // Sessions saved before the healthy-tester recalibration used another threshold
  const legacyScoring = thr > 0 && Math.abs(thr - sP95) > 0.5

  const domainData = Object.entries(domainT2).map(([gid, val]) => ({
    name:  DOMAIN_NAMES[Number(gid)] || `Topic ${gid}`,
    value: Number(Number(val).toFixed(1)),
    gid:   Number(gid),
  })).sort((a, b) => a.gid - b.gid)

  const levelData = Object.entries(levelT2).map(([lv, val]) => ({
    name:  LEVEL_NAMES[lv] || `Level ${lv}`,
    lv,
    value: Number(Number(val).toFixed(1)),
  })).sort((a, b) => a.lv.localeCompare(b.lv))

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

  const recs = clinicalRecs(flag, recLabel, psi, pai, phqScore, gadScore, domainT2, levelT2, iP95)

  // Plain-language reading of the three behaviour scores
  const t2Max   = Math.max(sP99 * 1.5, t2 * 1.08)
  const t2Verd  = t2 <= sP95 ? ['Within the healthy range', 'text-success-ink']
                : t2 <= sP99 ? ['Higher than most healthy adults', 'text-amber-ink']
                : ['Much higher than healthy adults', 'text-coral-ink']
  const indexCard = (kind, value) => {
    const pct = normComp?.[kind]?.pct
    const ref = HEALTHY_REF[kind]
    if (pct !== undefined) {
      const tone = pct >= 95 ? 'text-coral-ink' : pct >= 85 ? 'text-amber-ink' : 'text-success-ink'
      return {
        verdict: [percentileText(pct), tone],
        bar: <ScaleBar value={pct} markerLabel={percentileValue(pct)}
               zones={[{ to: 85, label: 'Typical', tone: 'good' }, { to: 95, label: 'Higher', tone: 'warn' }, { to: 100, label: 'Top 5%', tone: 'high' }]}
               ariaLabel={percentileText(pct)} />,
      }
    }
    const max = Math.max(ref.p95 * 1.5, value * 1.08)
    return {
      verdict: value > ref.p95 ? ['Above the healthy 95th percentile', 'text-coral-ink']
             : value > ref.p75 ? ['Above most healthy adults', 'text-amber-ink']
             : ['Within the healthy range', 'text-success-ink'],
      bar: <ScaleBar value={value} markerLabel={value.toFixed(1)}
             zones={[{ to: ref.p75, label: 'Typical', tone: 'good' }, { to: ref.p95, label: 'Higher', tone: 'warn' }, { to: max, label: 'Top 5%', tone: 'high' }]}
             ariaLabel={`${kind} ${value.toFixed(1)}`} />,
    }
  }
  const slow = indexCard('psi', psi)
  const rest = indexCard('pai', pai)
  const sessionDate = formatTimestamp(timestamp, { dateStyle: 'full', timeStyle: 'short' })
  const aboveDomains = domainData.filter(d => d.value > iP95)

  return (
    <MotionConfig reducedMotion="user">
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 overflow-y-auto" aria-label="Clinical assessment report">
        <div className="max-w-[1200px] mx-auto px-8 py-7" style={{ zoom: fontScale }}>

          {/* Top bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
            <button
              onClick={() => { setReport(null); navigate(sessionId ? `/clients/${student_id}` : '/dashboard') }}
              className="inline-flex items-center gap-2 text-tsub hover:text-tmain text-sm font-medium h-10 px-2 -ml-2 rounded-lg transition-colors cursor-pointer"
            >
              <ArrowLeft size={18} aria-hidden="true" /> {sessionId ? 'Back to client' : 'Back to dashboard'}
            </button>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 bg-white border border-border rounded-xl px-1.5 h-10 shadow-card" role="group" aria-label="Text size">
                <button onClick={decreaseFont} disabled={scaleIdx === 0} aria-label="Smaller text"
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold text-tsub hover:bg-bg hover:text-tmain transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer">A−</button>
                <span className="text-xs text-tsub px-1 select-none w-10 text-center font-semibold tabular-nums">{Math.round(fontScale * 100)}%</span>
                <button onClick={increaseFont} disabled={scaleIdx === FONT_SCALES.length - 1} aria-label="Larger text"
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-base font-bold text-tsub hover:bg-bg hover:text-tmain transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer">A+</button>
              </div>
              <button onClick={handleExport} disabled={exporting} className="btn-primary h-10 disabled:opacity-60 cursor-pointer">
                <Download size={16} aria-hidden="true" />
                {exporting ? 'Saving…' : 'Export report'}
              </button>
            </div>
          </div>
          {exportMsg && <p className="text-sm text-tmain bg-white border border-border rounded-xl px-4 py-2 mb-4" role="status">{exportMsg}</p>}

          {/* Title */}
          <header className="mb-6">
            <h1 className="text-3xl font-bold text-tmain">Assessment report</h1>
            <p className="text-tsub mt-1">
              Client <span className="font-semibold text-tmain">{student_id || '—'}</span>
              <span className="mx-2" aria-hidden="true">·</span>{sessionDate}
            </p>
          </header>

          <div className="space-y-9">
            <StatusHero flag={flag} label={analysis?.label} confidence={insufficient ? null : analysis?.confidence} pattern={analysis?.label} />

            {/* Key results */}
            <Section title="Key results" subtitle="Each bar shows where this client sits. The green part of each bar is the range seen in healthy adults.">
              <div className="grid md:grid-cols-2 gap-4">
                <ResultCard
                  title="Depression questionnaire" technical="PHQ-9 · client's own answers, last 2 weeks"
                  value={phqScore} valueSuffix="/ 27"
                  verdict={`${phqLabel(phqScore)} symptoms`}
                  verdictTone={phqScore >= 15 ? 'text-coral-ink' : phqScore >= 10 ? 'text-amber-ink' : 'text-success-ink'}
                >
                  <ScaleBar value={phqScore} markerLabel={String(phqScore)} ariaLabel={`PHQ-9 ${phqScore} of 27, ${phqLabel(phqScore)}`}
                    zones={[{ to: 4.5, label: 'Minimal', tone: 'good' }, { to: 9.5, label: 'Mild', tone: 'mild' }, { to: 14.5, label: 'Moderate', tone: 'warn' }, { to: 19.5, label: 'Mod. severe', tone: 'high' }, { to: 27, label: 'Severe', tone: 'high' }]} />
                </ResultCard>
                <ResultCard
                  title="Anxiety questionnaire" technical="GAD-7 · client's own answers, last 2 weeks"
                  value={gadScore} valueSuffix="/ 21"
                  verdict={`${gadLabel(gadScore)} symptoms`}
                  verdictTone={gadScore >= 15 ? 'text-coral-ink' : gadScore >= 10 ? 'text-amber-ink' : 'text-success-ink'}
                  delay={0.05}
                >
                  <ScaleBar value={gadScore} markerLabel={String(gadScore)} ariaLabel={`GAD-7 ${gadScore} of 21, ${gadLabel(gadScore)}`}
                    zones={[{ to: 4.5, label: 'Minimal', tone: 'good' }, { to: 9.5, label: 'Mild', tone: 'mild' }, { to: 14.5, label: 'Moderate', tone: 'warn' }, { to: 21, label: 'Severe', tone: 'high' }]} />
                </ResultCard>
              </div>

              {insufficient ? (
                <div className="card p-5 text-sm text-tmain">
                  Behaviour scores are not shown because too little typing was captured in this session.
                </div>
              ) : (
              <div className="grid lg:grid-cols-3 gap-4">
                <ResultCard
                  title="Overall behaviour change" technical={`Hotelling T² · change from own baseline`}
                  info={<InfoTooltip glossaryKey="T2" />}
                  value={t2.toFixed(1)}
                  verdict={t2Verd[0]} verdictTone={t2Verd[1]}
                  explain="How much the client's typing and mouse rhythm changed from their own calm baseline while answering the emotional prompts."
                  delay={0.1}
                >
                  <ScaleBar value={t2} markerLabel={t2.toFixed(0)} ariaLabel={`Overall change ${t2.toFixed(1)}: ${t2Verd[0]}`}
                    zones={[{ to: sP95, label: 'Typical', tone: 'good' }, { to: sP99, label: 'Higher', tone: 'warn' }, { to: t2Max, label: 'Much higher', tone: 'high' }]} />
                  {legacyScoring && (
                    <p className="text-xs text-tsub mt-2">This session was scored with an earlier calibration; its result label reflects that version.</p>
                  )}
                </ResultCard>
                <ResultCard
                  title="Slowing" technical={`Psychomotor Slowing Index · PSI ${psi.toFixed(1)}`}
                  info={<InfoTooltip glossaryKey="PSI" />}
                  value={normComp?.psi?.pct !== undefined ? percentileValue(normComp.psi.pct) : psi.toFixed(1)}
                  valueSuffix={normComp?.psi?.pct !== undefined ? 'percentile' : ''}
                  verdict={slow.verdict[0]} verdictTone={slow.verdict[1]}
                  explain="Slower key presses, longer key holds and more pauses than during calibration."
                  delay={0.15}
                >{slow.bar}</ResultCard>
                <ResultCard
                  title="Restlessness" technical={`Psychomotor Agitation Index · PAI ${pai.toFixed(1)}`}
                  info={<InfoTooltip glossaryKey="PAI" />}
                  value={normComp?.pai?.pct !== undefined ? percentileValue(normComp.pai.pct) : pai.toFixed(1)}
                  valueSuffix={normComp?.pai?.pct !== undefined ? 'percentile' : ''}
                  verdict={rest.verdict[0]} verdictTone={rest.verdict[1]}
                  explain="More irregular, jerky movement and more corrections than during calibration."
                  delay={0.2}
                >{rest.bar}</ResultCard>
              </div>
              )}
            </Section>

            {/* Where it showed up */}
            {(domainData.length > 0 || levelData.length > 0) && (
              <Section
                title="Where the changes showed up"
                subtitle={aboveDomains.length
                  ? `Bars above the dashed line are higher than in 95% of healthy adults: ${aboveDomains.map(d => d.name).join(', ')}.`
                  : 'All topics stayed below the dashed line — the level reached by 95% of healthy adults.'}
              >
                <div className="grid lg:grid-cols-2 gap-4">
                  {domainData.length > 0 && (
                    <div className="card p-5">
                      <h3 className="font-semibold text-tmain flex items-center">By topic of the prompt<InfoTooltip glossaryKey="DomainT2" /></h3>
                      <p className="text-sm text-tsub mb-3">Average change while answering prompts about each topic.</p>
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={domainData} margin={{ top: 16, right: 16, left: 0, bottom: 4 }}>
                          <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#557272' }} interval={0} />
                          <YAxis tick={{ fontSize: 11, fill: '#557272' }} width={44} domain={[0, dataMax => Math.ceil(Math.max(dataMax, iP95 * 1.15))]} />
                          <Tooltip cursor={{ fill: 'rgba(10,191,188,0.06)' }}
                            content={({ active, payload }) => {
                              if (!active || !payload?.length) return null
                              const d = payload[0].payload
                              return (
                                <div className="rounded-xl p-3 shadow-xl text-xs bg-tmain text-white max-w-[240px]">
                                  <p className="font-bold mb-1">{d.name}</p>
                                  <p className="mb-1">Change: <strong>{d.value}</strong> · typical up to {iP95.toFixed(0)}</p>
                                  <p className="text-white/75 leading-snug">{DOMAIN_TIPS[d.gid]}</p>
                                </div>
                              )
                            }}
                          />
                          <ReferenceLine y={iP95} stroke="#B83A38" strokeDasharray="5 3"
                            label={{ value: 'Typical limit', position: 'insideTopRight', fontSize: 11, fill: '#B83A38' }} />
                          <Bar dataKey="value" radius={[6, 6, 0, 0]} isAnimationActive>
                            {domainData.map((d, i) => <Cell key={i} fill={d.value > iP95 ? '#F27C7C' : '#7FD3D1'} />)}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                  {levelData.length > 0 && (
                    <div className="card p-5">
                      <h3 className="font-semibold text-tmain flex items-center">By strength of the prompt<InfoTooltip glossaryKey="LevelABC" /></h3>
                      <p className="text-sm text-tsub mb-3">A rising pattern from mild to strong prompts means the client reacted to emotional load.</p>
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={levelData} margin={{ top: 16, right: 16, left: 0, bottom: 4 }}>
                          <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#557272' }} interval={0} />
                          <YAxis tick={{ fontSize: 11, fill: '#557272' }} width={44} domain={[0, dataMax => Math.ceil(Math.max(dataMax, iP95 * 1.15))]} />
                          <Tooltip cursor={{ fill: 'rgba(10,191,188,0.06)' }}
                            content={({ active, payload }) => {
                              if (!active || !payload?.length) return null
                              const d = payload[0].payload
                              return (
                                <div className="rounded-xl p-3 shadow-xl text-xs bg-tmain text-white max-w-[230px]">
                                  <p className="font-bold mb-1">{d.name}</p>
                                  <p className="mb-1">Change: <strong>{d.value}</strong></p>
                                  <p className="text-white/75 leading-snug">{LEVEL_TIPS[d.lv]}</p>
                                </div>
                              )
                            }}
                          />
                          <ReferenceLine y={iP95} stroke="#B83A38" strokeDasharray="5 3"
                            label={{ value: 'Typical limit', position: 'insideTopRight', fontSize: 11, fill: '#B83A38' }} />
                          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                            {levelData.map((d, i) => <Cell key={i} fill={d.value > iP95 ? '#F27C7C' : '#7FD3D1'} />)}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>
              </Section>
            )}

            {/* Next steps + rationale */}
            <Section title="Suggested next steps" subtitle="Generated from the scores above. Use the ones that fit your clinical judgement.">
              <div className="grid lg:grid-cols-3 gap-4">
                <ol className="lg:col-span-2 grid sm:grid-cols-2 gap-4">
                  {recs.map((rec, i) => (
                    <motion.li key={i} className="card p-5 flex gap-4"
                      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.25, delay: 0.04 * i }}>
                      <span className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-ink text-white text-sm font-bold flex items-center justify-center" aria-hidden="true">{i + 1}</span>
                      <div className="min-w-0">
                        <p className="font-semibold text-tmain leading-snug mb-1">{rec.title}</p>
                        <p className="text-sm text-tsub leading-relaxed">{rec.desc}</p>
                      </div>
                    </motion.li>
                  ))}
                </ol>
                {analysis?.rationale && (
                  <aside className="card p-5 h-fit">
                    <h3 className="font-semibold text-tmain flex items-center gap-2 mb-2">
                      <Info size={18} className="text-accent-ink" aria-hidden="true" /> Why the system reached this result
                    </h3>
                    <p className="text-sm text-tmain leading-relaxed">{analysis.rationale}</p>
                  </aside>
                )}
              </div>
            </Section>

            {/* Specialist detail */}
            <Section title="Detailed analysis" subtitle="For specialists. Open a panel to see the underlying data.">
              <div className="space-y-3">
                <Collapsible icon={Activity} title="Hesitation and typing rhythm"
                  summary="Where the client paused before answering, and the rhythm of their key presses.">
                  <div className="grid xl:grid-cols-2 gap-4">
                    <TemporalHeatmap snapshots={snapshots} flag={flag} />
                    <Spectrogram flightTimes={flights} snapshots={snapshots} flag={flag} pai={pai} />
                  </div>
                  {histData.length > 0 && (
                    <div className="card p-5 mt-4">
                      <h3 className="font-semibold text-tmain mb-1">Time between key presses</h3>
                      <p className="text-sm text-tsub mb-3">How often each gap length occurred · {flights.length} key presses. Hover a bar for its meaning.</p>
                      <ResponsiveContainer width="100%" height={180}>
                        <BarChart data={histData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                          <XAxis dataKey="ms" tick={{ fontSize: 11, fill: '#557272' }} interval={2} />
                          <YAxis tick={{ fontSize: 11, fill: '#557272' }} width={44} />
                          <Tooltip cursor={{ fill: 'rgba(10,191,188,0.06)' }}
                            content={({ active, payload }) => {
                              if (!active || !payload?.length) return null
                              const d = payload[0].payload
                              const ms = parseInt(d.ms)
                              const signal = ms < 80 ? 'Very short — rushing or automatic typing'
                                : ms < 160 ? 'Fast-normal — efficient typing'
                                : ms < 280 ? 'Normal — calm, focused typing'
                                : ms < 450 ? 'Slightly slow — mild hesitation'
                                : 'Long — slowing or interrupted thinking'
                              return (
                                <div className="rounded-xl p-3 shadow-xl text-xs bg-tmain text-white max-w-[220px]">
                                  <p className="font-bold mb-1">{d.ms} gap</p>
                                  <p className="mb-1">{d.count} key presses</p>
                                  <p className="text-white/75 leading-snug">{signal}</p>
                                </div>
                              )
                            }}
                          />
                          <Bar dataKey="count" fill="#0ABFBC" radius={[3, 3, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </Collapsible>

                <Collapsible icon={Users} title="Comparison with healthy adults"
                  summary="Every score ranked against the healthy reference group (percentiles and z-scores).">
                  <NormativeComparison metrics={normComp} loading={normLoading} />
                </Collapsible>

                {snapshots.length > 0 && (
                  <Collapsible icon={ListChecks} title="Question-by-question breakdown"
                    summary={`${snapshots.length} prompts · ${snapshots.filter(s => s.flag === 'RED' || s.flag === 'AMBER').length} above typical`}>
                    <QuestionBreakdown snapshots={snapshots} itemP95={iP95} />
                  </Collapsible>
                )}
              </div>
            </Section>

            <p className="text-xs text-tsub text-center pb-6">
              PsyClick is a screening and decision-support tool. It does not diagnose a condition and does not replace evaluation by a qualified professional.
            </p>
          </div>
        </div>
      </main>
    </div>
    </MotionConfig>
  )
}
