import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, LogOut } from 'lucide-react'
import StageBar from '../components/StageBar.jsx'
import PasswordDialog from '../components/PasswordDialog.jsx'
import AnimatedBackground from '../components/AnimatedBackground.jsx'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'

const QUESTIONS = [
  { item_id:'A1', group_id:1, level:'A', domain_label:'time_workload',
    group_name:'Group 1: Time Pressure & Workload',
    level_name:'Level A - Descriptive / Low Emotional Load',
    prompt:'How do you pick which task to do first when you have many deadlines?' },
  { item_id:'A2', group_id:1, level:'A', domain_label:'time_workload',
    group_name:'Group 1: Time Pressure & Workload',
    level_name:'Level A - Descriptive / Low Emotional Load',
    prompt:'What does your daily routine look like during a very busy week?' },
  { item_id:'B1', group_id:1, level:'B', domain_label:'time_workload',
    group_name:'Group 1: Time Pressure & Workload',
    level_name:'Level B - Recall of Specific Events / Moderate Load',
    prompt:'How did you feel the last time a surprise task was added to your workload?' },
  { item_id:'C1', group_id:1, level:'C', domain_label:'time_workload',
    group_name:'Group 1: Time Pressure & Workload',
    level_name:'Level C - Self-Evaluation / Highest Psychomotor Activation',
    prompt:'How do you feel about yourself when you do not finish everything you planned to do?' },
  { item_id:'A3', group_id:2, level:'A', domain_label:'interpersonal',
    group_name:'Group 2: Interpersonal Friction',
    level_name:'Level A - Descriptive / Low Emotional Load',
    prompt:'How did your most recent misunderstanding with someone close to you get started?' },
  { item_id:'B2', group_id:2, level:'B', domain_label:'interpersonal',
    group_name:'Group 2: Interpersonal Friction',
    level_name:'Level B - Recall of Specific Events / Moderate Load',
    prompt:'How does it feel to have a conflict with your family that is not yet fixed?' },
  { item_id:'B3', group_id:2, level:'B', domain_label:'interpersonal',
    group_name:'Group 2: Interpersonal Friction',
    level_name:'Level B - Recall of Specific Events / Moderate Load',
    prompt:'How did you react the last time you felt you let down someone important?' },
  { item_id:'C2', group_id:2, level:'C', domain_label:'interpersonal',
    group_name:'Group 2: Interpersonal Friction',
    level_name:'Level C - Self-Evaluation / Highest Psychomotor Activation',
    prompt:'What did it feel like the last time you were left out of a group?' },
  { item_id:'A4', group_id:3, level:'A', domain_label:'performance_pressure',
    group_name:'Group 3: Performance Pressure',
    level_name:'Level A - Descriptive / Low Emotional Load',
    prompt:'What do you usually do to get ready for a big deadline or exam?' },
  { item_id:'B4', group_id:3, level:'B', domain_label:'performance_pressure',
    group_name:'Group 3: Performance Pressure',
    level_name:'Level B - Recall of Specific Events / Moderate Load',
    prompt:'How does your body feel when you have to speak in front of a panel or boss?' },
  { item_id:'C3', group_id:4, level:'C', domain_label:'self_area',
    group_name:'Group 4: Self Area',
    level_name:'Level C - Self-Evaluation / Highest Psychomotor Activation',
    prompt:'What doubts do you have when you think about a big decision you made recently?' },
  { item_id:'C4', group_id:4, level:'C', domain_label:'self_area',
    group_name:'Group 4: Self Area',
    level_name:'Level C - Self-Evaluation / Highest Psychomotor Activation',
    prompt:'What words do you use to describe yourself on days when things are very hard?' },
]

const LEVEL_COLORS = {
  A: { bg: 'bg-success/15', text: 'text-success', border: 'border-success', badge: 'Low Load' },
  B: { bg: 'bg-amber/15', text: 'text-amber', border: 'border-amber', badge: 'Moderate Load' },
  C: { bg: 'bg-coral/15', text: 'text-coral', border: 'border-coral', badge: 'High Load' },
}

const IDLE_MS = 30_000   // 30s — 10s was too aggressive during emotional reflection

export default function EmotionalTask() {
  const navigate = useNavigate()
  const { setReport, user, setUser, setClient } = useApp()

  const [qi, setQi] = useState(0)
  const [responses, setResponses] = useState(Array(QUESTIONS.length).fill(''))
  const [showPwd, setShowPwd] = useState(false)
  const [showExitPwd, setShowExitPwd] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const wordRefs = useRef([])
  const idleTimer = useRef(null)
  const textareaRef = useRef(null)

  const q = QUESTIONS[qi]
  const total = QUESTIONS.length
  const response = responses[qi] || ''
  const lc = LEVEL_COLORS[q.level] || LEVEL_COLORS.A
  const pct = Math.round(((qi + 1) / total) * 100)

  useEffect(() => {
    api.emotionalStart()
  }, [])

  useEffect(() => {
    api.questionSet(q)
    resetIdle()
    setTimeout(() => textareaRef.current?.focus(), 50)
    setTimeout(() => {
      textareaRef.current?.focus()
      textareaRef.current?.click()
    }, 150)
  }, [qi]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const timer = setTimeout(() => {
      const words = q.prompt.split(' ')
      const boxes = wordRefs.current
        .filter(Boolean)
        .map((el, wi) => {
          const r = el.getBoundingClientRect()
          // pynput uses screen-relative coordinates.
          // window.screenX/Y gives the position of the browser window on the screen.
          // We must account for the title bar / window chrome to get the true screen position of the viewport.
          const dpr = window.devicePixelRatio || 1
          const vOffset = window.outerHeight - window.innerHeight
          const hOffset = (window.outerWidth - window.innerWidth) / 2
          return {
            word: words[wi] || '',
            x1: Math.round(window.screenX + (hOffset + r.left - 20) * dpr),
            y1: Math.round(window.screenY + (vOffset + r.top - 20) * dpr),
            x2: Math.round(window.screenX + (hOffset + r.right + 20) * dpr),
            y2: Math.round(window.screenY + (vOffset + r.bottom + 20) * dpr),
          }
        })
      if (boxes.length) api.wordBoxes(boxes)
    }, 20)
    return () => clearTimeout(timer)
  }, [qi]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => clearTimeout(idleTimer.current), [])

  function resetIdle() {
    clearTimeout(idleTimer.current)
    idleTimer.current = setTimeout(() => {
      api.auditIdle(`Q${qi + 1} of ${total}`)
    }, IDLE_MS)
  }

  function updateResponse(value) {
    const next = [...responses]
    next[qi] = value
    setResponses(next)
    resetIdle()
  }

  async function saveCurrentSnapshot() {
    try {
      await api.questionSnapshot(q, response, qi, total)
    } catch (_) {
      // Non-fatal: allow the client to keep moving even if a snapshot misses.
    }
  }

  async function handlePreviousQuestion() {
    if (qi === 0 || busy) return
    setErr('')
    setBusy(true)
    await saveCurrentSnapshot()
    setBusy(false)
    setQi(qi - 1)
  }

  async function handleNext() {
    setErr('')
    setBusy(true)
    await saveCurrentSnapshot()
    setBusy(false)

    const nextQi = qi + 1
    if (nextQi < total) {
      setQi(nextQi)
    } else {
      setShowPwd(true)
    }
  }

  async function handleFinish() {
    setShowPwd(false)
    setBusy(true)
    const res = await api.assessmentFinish()
    setBusy(false)
    if (res.success && res.report) {
      setReport(res.report)
      navigate('/report')
    } else {
      setErr(res.error || 'Failed to process results. Please ensure biometric capture completed.')
    }
  }

  function handleExitToLogin() {
    setShowExitPwd(false)
    setReport(null)
    setClient(null)
    setUser(null)
    navigate('/')
  }
  // Clear refs to populate them freshly during render
  wordRefs.current = []

  return (
    <div className="h-screen overflow-y-auto bg-bg assessment-bg">
    <AnimatedBackground />
      <button
        type="button"
        onClick={() => setShowExitPwd(true)}
        className="fixed left-6 top-6 z-40 inline-flex items-center gap-2 rounded-full border border-border bg-white/90 px-5 py-3 text-base font-bold text-tmain shadow-card backdrop-blur transition-colors hover:border-coral/50 hover:text-coral"
      >
        <LogOut size={20} />
        Exit Session
      </button>

      <div className="flex min-h-screen flex-col items-center px-6 py-10 animate-fade-in">
        <img src={`${import.meta.env.BASE_URL}images/LOGOggg.png`} alt="PsyClick" className="mb-6 h-14 w-14 object-contain" />

        <div className="w-full max-w-5xl">
          <StageBar active={2} />

          <div className="mb-4 text-center">
            <h1 className="mb-1 text-4xl font-bold text-tmain">Emotional Response Task</h1>
            <p className="text-lg text-tsub">Respond in your own words — there are no right or wrong answers.</p>
          </div>

          {/* Progress bar with count label above it */}
          <div className="mb-5">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold text-tsub uppercase tracking-wide">Progress</span>
              <span className="text-xs font-bold text-accent">{qi + 1} / {total}</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-border">
              <div className="h-full rounded-full bg-accent transition-all duration-500" style={{ width: `${pct}%` }} />
            </div>
          </div>

          <div className={`mb-5 flex flex-wrap items-center justify-between gap-3 rounded-[18px] border-l-4 p-5 ${lc.border} ${lc.bg}`}>
            <span className={`text-base font-bold ${lc.text}`}>{q.group_name}</span>
            <span className={`rounded-full bg-white/80 px-4 py-1.5 text-sm font-bold ${lc.text}`}>{lc.badge}</span>
          </div>

          <div className="card mb-5 p-9">
            <p className="text-center text-2xl font-semibold leading-relaxed text-tmain">
              {q.prompt.split(' ').map((word, wi) => (
                <span
                  key={`${qi}-${wi}`}
                  ref={el => { wordRefs.current[wi] = el }}
                  className="mr-1 inline-block"
                >
                  {word}
                </span>
              ))}
            </p>
          </div>

          <div className="card mb-5 p-7">
            <p className="mb-4 text-center text-sm font-semibold uppercase tracking-wide text-tsub">Your Response</p>
            <textarea
              ref={textareaRef}
              className="input-field min-h-[220px] resize-none cursor-text text-lg leading-relaxed"
              value={response}
              maxLength={800}
              onChange={e => updateResponse(e.target.value)}
              onKeyDown={() => resetIdle()}
              onFocus={() => resetIdle()}
              onClick={() => { textareaRef.current?.focus(); resetIdle() }}
              placeholder="Type your response here..."
              autoComplete="off"
            />
            <p className={`mt-3 text-right text-sm font-semibold ${response.length >= 750 ? 'text-coral' : 'text-tsub'}`}>
              {response.length}/800
            </p>
          </div>

          {err && (
            <div className="mb-4 rounded-card border border-coral/30 bg-coral/10 p-4 text-base font-medium text-coral">
              {err}
            </div>
          )}

          <div className="mb-8 grid grid-cols-[0.7fr_1fr] gap-4">
            <button
              type="button"
              onClick={handlePreviousQuestion}
              disabled={qi === 0 || busy}
              className="btn-outline h-14 justify-center text-base disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ArrowLeft size={20} />
              Previous Question
            </button>
            <button
              onClick={handleNext}
              disabled={busy}
              className="btn-primary h-14 text-lg disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy
                ? 'Saving...'
                : qi + 1 < total
                  ? 'Next Question →'
                  : 'Complete Assessment →'}
            </button>
          </div>
        </div>

        {showPwd && (
          <PasswordDialog onConfirm={handleFinish} onCancel={() => setShowPwd(false)} />
        )}
        {showExitPwd && (
          <PasswordDialog onConfirm={handleExitToLogin} onCancel={() => setShowExitPwd(false)} />
        )}
      </div>
    </div>
  )
}
