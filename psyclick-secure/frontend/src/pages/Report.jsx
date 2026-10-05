import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion, MotionConfig } from 'motion/react'
import { ArrowLeft, FileDown, Lock, Users, ListChecks, ShieldAlert, Plus, FolderOpen } from 'lucide-react'
import Sidebar from '../components/Sidebar.jsx'
import { StatusHero, Section, Collapsible, ScaleBar, ResultCard } from '../components/ReportParts.jsx'
import { useToast } from '../components/ui.jsx'
import { formatTimestamp } from '../lib/status.jsx'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import InfoTooltip from '../report/InfoTooltip.jsx'
import { SessionTrace, TopicGrid, RhythmChart, ChangeSince } from '../report/visuals.jsx'
import ReadingHeatmap from '../report/ReadingHeatmap.jsx'
import { collectSignals, SignalsList } from '../report/signals.jsx'
import { KpiStrip, ProfileRadar } from '../report/overview.jsx'
import { NormativeComparison, QuestionBreakdown, percentileText, percentileValue } from '../report/detail.jsx'
import { HEALTHY_REF, ITEM9_LABEL, phqLabel, gadLabel, clinicalRecs } from '../report/text.js'

const FALLBACK_THRESHOLDS = { session: { p95: 77.8, p99: 114.1 }, item: { p95: 526.4, p99: 932.9 } }
const FONT_SCALES = [0.85, 1, 1.15, 1.3]
const nextFrame = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))
const wait = ms => new Promise(r => setTimeout(r, ms))

function Panel({ title, info, caption, children, className = '' }) {
  return (
    <section className={`surface p-6 print-avoid ${className}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-display text-lg font-semibold text-[#0F2A33] flex items-center">{title}{info && <InfoTooltip glossaryKey={info} />}</h3>
          {caption && <p className="text-sm text-[#4A6670] mt-0.5 max-w-[72ch]">{caption}</p>}
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  )
}

export default function Report() {
  const navigate        = useNavigate()
  const { sessionId }   = useParams()
  const { report: ctxReport, setReport } = useApp()
  const toast = useToast()

  const [data,        setData]        = useState(null)
  const [normComp,    setNormComp]    = useState(null)
  const [normLoading, setNormLoading] = useState(true)
  const [thresholds,  setThresholds]  = useState(FALLBACK_THRESHOLDS)
  const [history,     setHistory]     = useState(null)
  const [busy,        setBusy]        = useState('')      // '' | 'pdf' | 'encrypted'
  const [printing,    setPrinting]    = useState(false)
  const [err,         setErr]         = useState('')
  const [fontScale,   setFontScale]   = useState(1)
  const scaleIdx = Math.max(0, FONT_SCALES.indexOf(fontScale))

  useEffect(() => {
    api.normativeStats().then(d => { if (d?.thresholds?.session) setThresholds(d.thresholds) }).catch(() => {})
  }, [])

  useEffect(() => {
    function loadCompare(sid) {
      setNormLoading(true)
      api.normativeCompare(sid).then(d => {
        const metrics = d?.available ? d.metrics : (d?.t2_score || d?.psi) ? d : null
        if (metrics) setNormComp(metrics)
        setNormLoading(false)
      }).catch(() => setNormLoading(false))
    }
    if (sessionId) {
      api.sessionDetail(sessionId).then(d => { if (d.error) setErr(d.error); else setData(d) })
      loadCompare(sessionId)
    } else if (ctxReport) {
      setData(ctxReport)
      if (ctxReport?.session_id) loadCompare(ctxReport.session_id)
      else setNormLoading(false)
    }
  }, [sessionId, ctxReport])

  useEffect(() => {
    if (!data?.student_id) return
    api.clientSessions(data.student_id).then(d => setHistory(Array.isArray(d) ? d : []))
  }, [data?.student_id])

  // PDF: render the full report (all panels open, toolbar hidden) and let the
  // clinician choose where to save it. Electron renders a real PDF; in a
  // browser the print dialog offers "Save as PDF" with the same layout.
  async function savePdf() {
    if (!data) return
    setBusy('pdf'); setPrinting(true)
    await nextFrame(); await wait(700)
    const day = (formatTimestamp(data.timestamp, { year: 'numeric', month: '2-digit', day: '2-digit' }) || '').replace(/\//g, '-')
    const name = `PsyClick report ${data.student_id || 'client'} ${day}.pdf`
    try {
      if (window.electron?.saveReportPdf) {
        const res = await window.electron.saveReportPdf({ defaultName: name })
        if (res?.filePath) {
          api.auditLog('clinician', 'Saved report as PDF', `${data.student_id} · session ${sessionId || data.session_id || ''}`)
          toast(`Saved to ${res.filePath}`)
          window.electron?.showInFolder?.(res.filePath)
        } else if (res?.error) toast(res.error, 'error')
      } else {
        api.auditLog('clinician', 'Printed report', `${data.student_id} · session ${sessionId || data.session_id || ''}`)
        window.print()
      }
    } finally {
      setPrinting(false); setBusy('')
    }
  }

  async function saveEncrypted() {
    setBusy('encrypted')
    const res = await api.exportReport(data)
    setBusy('')
    if (res.success && res.file) toast('Encrypted copy saved in the PsyClick secure folder.')
    else toast(res.error || 'The encrypted copy could not be saved.', 'error')
  }

  if (err) return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 flex items-center justify-center p-8 app-canvas">
        <div className="bg-white rounded-2xl border border-border p-10 max-w-md text-center" role="alert">
          <p className="font-display text-xl font-semibold text-tmain">This report could not be opened</p>
          <p className="text-tsub mt-2">{err}</p>
          <button onClick={() => navigate('/clients')} className="btn-primary mt-6 h-11">Back to clients</button>
        </div>
      </main>
    </div>
  )

  if (!data && !sessionId && !ctxReport) return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 flex items-center justify-center p-8 app-canvas">
        <div className="bg-white rounded-2xl border border-border p-10 max-w-md text-center">
          <p className="font-display text-xl font-semibold text-tmain">No report is open</p>
          <p className="text-tsub mt-2">Open a session from the client list to see its report.</p>
          <button onClick={() => navigate('/clients')} className="btn-primary mt-6 h-11">Go to clients</button>
        </div>
      </main>
    </div>
  )

  if (!data) return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 flex items-center justify-center app-canvas">
        <p className="text-tsub" role="status">Loading report…</p>
      </main>
    </div>
  )

  const { student_id, timestamp, phq, gad, analysis, visuals } = data
  const flag      = analysis?.flag || 'GREEN'
  const snapshots = visuals?.question_snapshots || []
  const domainT2  = visuals?.domain_t2 || {}
  const levelT2   = visuals?.level_t2 || {}
  const flights   = visuals?.flight_times || []
  const t2  = analysis?.t2_score ?? 0
  const thr = analysis?.t2_threshold ?? 0
  const psi = analysis?.psi ?? 0
  const pai = analysis?.pai ?? 0
  const insufficient = analysis?.label === 'Insufficient Data'
  const phqScore = phq?.score ?? 0
  const gadScore = gad?.score ?? 0
  const item9    = phq?.item9 ?? 0
  const safety   = item9 > 0
  const sP95 = thresholds.session.p95, sP99 = thresholds.session.p99
  const iP95 = thresholds.item.p95, iP99 = thresholds.item.p99
  const legacyScoring = thr > 0 && Math.abs(thr - sP95) > 0.5
  const thisSession = sessionId || data.session_id

  const recs = clinicalRecs({ flag, label: analysis?.label || '', psi, pai, phq: phqScore, gad: gadScore, domainT2, levelT2, itemP95: iP95, item9 })

  const t2Max  = Math.max(sP99 * 1.5, t2 * 1.08)
  const t2Verd = t2 <= sP95 ? ['Within the healthy range', 'text-success-ink']
               : t2 <= sP99 ? ['Higher than most healthy adults', 'text-amber-ink']
               : ['Much higher than healthy adults', 'text-coral-ink']
  const indexCard = (kind, value) => {
    const pct = normComp?.[kind]?.pct
    const ref = HEALTHY_REF[kind]
    if (pct !== undefined) {
      return {
        value: percentileValue(pct), suffix: 'percentile',
        verdict: [percentileText(pct), pct >= 95 ? 'text-coral-ink' : pct >= 85 ? 'text-amber-ink' : 'text-success-ink'],
        bar: <ScaleBar value={pct} markerLabel={percentileValue(pct)} ariaLabel={percentileText(pct)}
               zones={[{ to: 85, label: 'Typical', tone: 'good' }, { to: 95, label: 'Higher', tone: 'warn' }, { to: 100, label: 'Top 5%', tone: 'high' }]} />,
      }
    }
    const max = Math.max(ref.p95 * 1.5, value * 1.08)
    return {
      value: value.toFixed(1), suffix: '',
      verdict: value > ref.p95 ? ['Above the healthy 95th percentile', 'text-coral-ink'] : value > ref.p75 ? ['Above most healthy adults', 'text-amber-ink'] : ['Within the healthy range', 'text-success-ink'],
      bar: <ScaleBar value={value} markerLabel={value.toFixed(1)} ariaLabel={`${kind} ${value.toFixed(1)}`}
             zones={[{ to: ref.p75, label: 'Typical', tone: 'good' }, { to: ref.p95, label: 'Higher', tone: 'warn' }, { to: max, label: 'Top 5%', tone: 'high' }]} />,
    }
  }
  const slow = indexCard('psi', psi)
  const rest = indexCard('pai', pai)
  const scoredItems = snapshots.filter(s => s.flag !== 'NO_DATA')
  const aboveItems  = scoredItems.filter(s => Number(s.t2_score) > iP95)

  return (
    <MotionConfig reducedMotion="user">
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 overflow-y-auto app-canvas" aria-label="Clinical assessment report">
        <div className={`report-root mx-auto px-8 py-7 ${printing ? 'w-[1040px]' : 'max-w-[1200px]'}`} style={{ zoom: printing ? 1 : fontScale }}>

          {/* Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-6" data-print-hide>
            <button onClick={() => { setReport(null); navigate(sessionId ? `/clients/${student_id}` : '/dashboard') }}
              className="inline-flex items-center gap-2 text-tsub hover:text-tmain font-medium h-10 px-2 -ml-2 rounded-lg cursor-pointer">
              <ArrowLeft size={18} aria-hidden="true" /> {sessionId ? `Back to ${student_id}` : 'Back to dashboard'}
            </button>
            <div className="flex flex-wrap items-center gap-2">
              {student_id && (
                <button onClick={() => navigate(`/intake?client=${encodeURIComponent(student_id)}`)}
                  className="h-10 px-4 rounded-xl border border-[#D9E6EA] bg-white text-sm font-semibold text-tmain hover:border-[#0A6B80]/50 inline-flex items-center gap-2 cursor-pointer">
                  <Plus size={16} aria-hidden="true" /> New session
                </button>
              )}
              <div className="flex items-center gap-1 bg-white border border-[#D9E6EA] rounded-xl px-1.5 h-10" role="group" aria-label="Text size">
                <button onClick={() => setFontScale(FONT_SCALES[scaleIdx - 1])} disabled={scaleIdx === 0} aria-label="Smaller text"
                  className="w-8 h-8 rounded-lg text-sm font-bold text-tsub hover:bg-bg disabled:opacity-40 cursor-pointer">A−</button>
                <span className="font-mono text-xs text-tsub w-10 text-center">{Math.round(fontScale * 100)}%</span>
                <button onClick={() => setFontScale(FONT_SCALES[scaleIdx + 1])} disabled={scaleIdx === FONT_SCALES.length - 1} aria-label="Larger text"
                  className="w-8 h-8 rounded-lg text-base font-bold text-tsub hover:bg-bg disabled:opacity-40 cursor-pointer">A+</button>
              </div>
              <button onClick={saveEncrypted} disabled={!!busy} title="Save an encrypted copy in PsyClick's secure folder"
                className="h-10 px-3.5 rounded-xl text-sm font-semibold text-tsub hover:text-tmain hover:bg-black/[0.04] inline-flex items-center gap-2 cursor-pointer disabled:opacity-50">
                <Lock size={15} aria-hidden="true" /> {busy === 'encrypted' ? 'Saving…' : 'Encrypted copy'}
              </button>
              <button onClick={savePdf} disabled={!!busy}
                className="btn-primary h-10 px-4 rounded-xl text-sm inline-flex items-center gap-2 cursor-pointer disabled:opacity-60">
                {busy === 'pdf' ? <FolderOpen size={16} aria-hidden="true" /> : <FileDown size={16} aria-hidden="true" />}
                {busy === 'pdf' ? 'Choose a folder…' : 'Save as PDF'}
              </button>
            </div>
          </div>

          {/* Title block */}
          <header className="mb-7 flex flex-wrap items-end justify-between gap-4 border-b border-[#D9E6EA] pb-6">
            <div>
              <p className="font-mono text-sm text-[#4A6670]">Client {student_id || '—'}{thisSession ? ` · session ${thisSession}` : ''}</p>
              <h1 className="font-display text-[34px] leading-tight font-semibold text-[#0F2A33] mt-1">Assessment report</h1>
              <p className="text-[#4A6670] mt-1">{formatTimestamp(timestamp, { dateStyle: 'full', timeStyle: 'short' })}</p>
            </div>
            <p className="text-xs text-[#4A6670] max-w-[34ch] text-right">Screening and decision support. Not a diagnosis.</p>
          </header>

          <div className="space-y-6">
            {safety && (
              <div role="alert" className="rounded-2xl border-2 border-coral-ink bg-[#FBEDEC] p-5 flex gap-4 items-start print-avoid">
                <ShieldAlert size={28} className="text-coral-ink flex-shrink-0 mt-0.5" aria-hidden="true" />
                <div>
                  <p className="font-display text-lg font-semibold text-coral-ink">Thoughts of self-harm reported</p>
                  <p className="text-[#0F2A33] mt-1">
                    PHQ-9 question 9 — “thoughts that you would be better off dead, or of hurting yourself” — was answered
                    <strong> “{ITEM9_LABEL[item9]}”</strong>. Complete a structured suicide-risk assessment in this session, whatever the result below.
                  </p>
                </div>
              </div>
            )}

            <StatusHero flag={flag} label={analysis?.label} confidence={insufficient ? null : analysis?.confidence} pattern={analysis?.label} />

            <KpiStrip t2={t2} sP95={sP95} sP99={sP99} insufficient={insufficient} phq={phqScore} gad={gadScore} item9={item9}
              snapshots={snapshots} iP95={iP95} iP99={iP99} history={history} sessionId={thisSession} />

            <div className="grid xl:grid-cols-[1.4fr_1fr] print:grid-cols-[1.4fr_1fr] gap-6 items-stretch">
              <Panel title="What stood out"
                caption="Every signal in this session, most urgent first — including small ones that did not change the overall result. Small signals are where early changes show first.">
                <SignalsList signals={collectSignals({ item9, phq: phqScore, gad: gadScore, t2: insufficient ? 0 : t2, sP95, label: analysis?.label,
                  psiPct: insufficient ? null : normComp?.psi?.pct, paiPct: insufficient ? null : normComp?.pai?.pct,
                  snapshots, iP95, levelT2, history, sessionId: thisSession })} />
              </Panel>
              <Panel title="Profile against healthy adults"
                caption="Each corner is one score, ranked against healthy adults. The further out, the more unusual.">
                {normLoading ? <p className="text-sm text-tsub" role="status">Loading comparison…</p>
                  : <ProfileRadar metrics={normComp} insufficient={insufficient} />}
              </Panel>
            </div>

            {/* The session, prompt by prompt — the signature view */}
            {snapshots.length > 0 && (
              <Panel title="The session, prompt by prompt" info="Trace"
                caption={insufficient ? 'Too little typing was captured to score the prompts.'
                  : aboveItems.length
                    ? `${aboveItems.length} of ${scoredItems.length} prompts rose above the healthy range: ${aboveItems.map(s => s.item_id).join(', ')}. Hover a prompt to read it.`
                    : `All ${scoredItems.length} scored prompts stayed in the healthy range. Hover a prompt to read it.`}>
                <SessionTrace snapshots={snapshots} itemP95={iP95} itemP99={iP99} />
              </Panel>
            )}

            {/* Where attention lingered while reading */}
            {snapshots.length > 0 && (
              <Panel title="Where attention lingered" info="Reading"
                caption="Each prompt as the client saw it. Words are tinted by how long the cursor rested on them while reading — ask about the darkest ones.">
                <ReadingHeatmap snapshots={snapshots} />
              </Panel>
            )}

            {/* Where + questionnaires */}
            <div className="grid xl:grid-cols-[1.25fr_1fr] print:grid-cols-[1.25fr_1fr] gap-6 items-start">
              {snapshots.length > 0 && (
                <Panel title="Where the change happened" info="Grid"
                  caption="Rows are topics, columns are how emotionally strong the prompt was.">
                  <TopicGrid snapshots={snapshots} itemP95={iP95} />
                </Panel>
              )}
              <div className="grid gap-4">
                <ResultCard title="Depression questionnaire" technical="PHQ-9 · client's own answers, last 2 weeks"
                  value={phqScore} valueSuffix="/ 27" verdict={`${phqLabel(phqScore)} symptoms`}
                  verdictTone={phqScore >= 15 ? 'text-coral-ink' : phqScore >= 10 ? 'text-amber-ink' : 'text-success-ink'}>
                  <ScaleBar value={phqScore} markerLabel={String(phqScore)} ariaLabel={`PHQ-9 ${phqScore} of 27, ${phqLabel(phqScore)}`}
                    zones={[{ to: 4.5, label: 'Minimal', tone: 'good' }, { to: 9.5, label: 'Mild', tone: 'mild' }, { to: 14.5, label: 'Moderate', tone: 'warn' }, { to: 19.5, label: 'Mod. severe', tone: 'high' }, { to: 27, label: 'Severe', tone: 'high' }]} />
                </ResultCard>
                <ResultCard title="Anxiety questionnaire" technical="GAD-7 · client's own answers, last 2 weeks"
                  value={gadScore} valueSuffix="/ 21" verdict={`${gadLabel(gadScore)} symptoms`}
                  verdictTone={gadScore >= 15 ? 'text-coral-ink' : gadScore >= 10 ? 'text-amber-ink' : 'text-success-ink'}>
                  <ScaleBar value={gadScore} markerLabel={String(gadScore)} ariaLabel={`GAD-7 ${gadScore} of 21, ${gadLabel(gadScore)}`}
                    zones={[{ to: 4.5, label: 'Minimal', tone: 'good' }, { to: 9.5, label: 'Mild', tone: 'mild' }, { to: 14.5, label: 'Moderate', tone: 'warn' }, { to: 21, label: 'Severe', tone: 'high' }]} />
                </ResultCard>
              </div>
            </div>

            {/* Behaviour summary */}
            {!insufficient && (
              <div className="grid lg:grid-cols-3 print:grid-cols-3 gap-4">
                <ResultCard title="Overall behaviour change" technical="Hotelling T² · vs. the client's own warm-up"
                  info={<InfoTooltip glossaryKey="T2" />} value={t2.toFixed(1)} verdict={t2Verd[0]} verdictTone={t2Verd[1]}>
                  <ScaleBar value={t2} markerLabel={t2.toFixed(0)} ariaLabel={`Overall change ${t2.toFixed(1)}: ${t2Verd[0]}`}
                    zones={[{ to: sP95, label: 'Typical', tone: 'good' }, { to: sP99, label: 'Higher', tone: 'warn' }, { to: t2Max, label: 'Much higher', tone: 'high' }]} />
                  {legacyScoring && <p className="text-xs text-tsub mt-2">Scored with an earlier calibration; the result label reflects that version.</p>}
                </ResultCard>
                <ResultCard title="Slowing" technical={`Psychomotor Slowing Index · ${psi.toFixed(1)}`}
                  info={<InfoTooltip glossaryKey="PSI" />} value={slow.value} valueSuffix={slow.suffix}
                  verdict={slow.verdict[0]} verdictTone={slow.verdict[1]}>{slow.bar}</ResultCard>
                <ResultCard title="Restlessness" technical={`Psychomotor Agitation Index · ${pai.toFixed(1)}`}
                  info={<InfoTooltip glossaryKey="PAI" />} value={rest.value} valueSuffix={rest.suffix}
                  verdict={rest.verdict[0]} verdictTone={rest.verdict[1]}>{rest.bar}</ResultCard>
              </div>
            )}

            {/* Personal baseline over time */}
            <Panel title={`Since ${student_id}'s earlier sessions`}
              caption="Early warning comes from change within the same person, so each visit is compared with their own history.">
              <ChangeSince sessions={history} sessionId={thisSession} sessionP95={sP95} />
            </Panel>

            {/* Rhythm + reasoning | next steps */}
            <div className="grid xl:grid-cols-[1.25fr_1fr] print:grid-cols-[1.25fr_1fr] gap-6 items-start">
              <div className="space-y-6">
                <Panel title="Typing rhythm" info="Rhythm" caption="Gaps between key presses while writing the answers.">
                  <RhythmChart flights={flights} />
                </Panel>
                {analysis?.rationale && (
                  <Panel title="How the result was reached">
                    <p className="text-sm text-[#0F2A33] leading-relaxed font-mono">{analysis.rationale}</p>
                  </Panel>
                )}
              </div>
              <Panel title="Suggested next steps" caption="Use the ones that fit your clinical judgement.">
                <ol className="space-y-3">
                  {recs.map((r, i) => (
                    <motion.li key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.04 * i, duration: 0.25 }}
                      className="flex gap-3">
                      <span className={`mt-1.5 w-2.5 h-2.5 rounded-full flex-shrink-0 ${r.tone === 'coral' ? 'bg-coral-ink' : r.tone === 'amber' ? 'bg-[#B7791F]' : 'bg-[#0A6B80]'}`} aria-hidden="true" />
                      <div>
                        <p className="font-semibold text-[#0F2A33] leading-snug">{r.title}</p>
                        <p className="text-sm text-[#4A6670] leading-relaxed">{r.desc}</p>
                      </div>
                    </motion.li>
                  ))}
                </ol>
              </Panel>
            </div>

            {/* Specialist tables */}
            <div className="space-y-3">
              <Collapsible icon={Users} forceOpen={printing} title="Comparison with healthy adults"
                summary="Every score ranked against the healthy reference group, with z-scores.">
                <NormativeComparison metrics={normComp} loading={normLoading} />
              </Collapsible>
              {snapshots.length > 0 && (
                <Collapsible icon={ListChecks} forceOpen={printing} title="Prompt-by-prompt table"
                  summary={`${snapshots.length} prompts · ${aboveItems.length} above the healthy range`}>
                  <QuestionBreakdown snapshots={snapshots} itemP95={iP95} />
                </Collapsible>
              )}
            </div>

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
