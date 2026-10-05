import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import { ArrowLeft, ArrowRight, Check, Lightbulb } from 'lucide-react'
import { api } from '../api/psyclick.js'
import AssessmentShell, { StepHeading, useStepStart } from '../components/AssessmentShell.jsx'
import { Button, Alert, EASE } from '../components/ui.jsx'

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

const IDLE_MS = 30_000          // reflection pauses are normal; only log long idles
const SHORT_ANSWER = 20         // answers below this are excluded from the main score
const HOVER_MIN_MS = 100        // a cursor rest this long over a word counts as reading it
const HOVER_CAP_MS = 5000       // one rest counts for at most 5 s (hand off the mouse)
const AWAY_MS = 60_000          // this long before the first key is time away, not hesitation

// Reading measures taken in the page itself: page coordinates and the page
// clock, so they hold at any display scaling, on any monitor, and for
// keyboard-only users (the pause no longer depends on the mouse moving).
function newVisit() {
  return { shownAt: performance.now(), firstKeyAt: null, blurredMs: 0, blurAt: null, lostFocus: false,
           lastMoveAt: null, lastWord: null, lastKeyAt: 0, hover: {} }
}

export default function EmotionalTask() {
  const navigate = useNavigate()
  const [qi, setQi]               = useState(0)
  const [responses, setResponses] = useState(Array(QUESTIONS.length).fill(''))
  const [busy, setBusy]           = useState(false)
  const [notice, setNotice]       = useState('')

  const wordRefs    = useRef([])
  const idleTimer   = useRef(null)
  const textareaRef = useRef(null)
  const visit       = useRef(newVisit())

  const q = QUESTIONS[qi]
  const total = QUESTIONS.length
  const response = responses[qi] || ''
  const trimmed = response.trim().length
  const isLast = qi + 1 === total

  const lost = useStepStart(api.emotionalStart)

  useEffect(() => {
    api.questionSet(q)
    visit.current = newVisit()
    resetIdle()
    setNotice('')
    const t = setTimeout(() => textareaRef.current?.focus(), 120)
    return () => clearTimeout(t)
  }, [qi]) // eslint-disable-line react-hooks/exhaustive-deps

  // Cursor rests over prompt words, and time the window was not focused
  useEffect(() => {
    const credit = (v, now) => {
      // the cursor sat still on lastWord since lastMoveAt; typing in between means it was not reading
      if (v.lastWord == null || v.lastMoveAt == null || v.lastKeyAt > v.lastMoveAt) return
      const gap = now - v.lastMoveAt
      if (gap < HOVER_MIN_MS) return
      const h = v.hover[v.lastWord] || (v.hover[v.lastWord] = { word: v.lastWord, dwell_ms: 0, hover_count: 0 })
      h.dwell_ms += Math.min(gap, HOVER_CAP_MS)
      h.hover_count += 1
    }
    const onMove = e => {
      const v = visit.current, now = performance.now()
      credit(v, now)
      v.lastMoveAt = now
      const el = e.target?.closest?.('[data-word]')
      v.lastWord = el ? el.dataset.word : null
    }
    const onBlur = () => {
      const v = visit.current, now = performance.now()
      credit(v, now)
      v.lastWord = null
      if (v.blurAt == null) v.blurAt = now
    }
    const onFocus = () => {
      const v = visit.current
      if (v.blurAt != null) {
        if (v.firstKeyAt == null) { v.blurredMs += performance.now() - v.blurAt; v.lostFocus = true }
        v.blurAt = null
      }
    }
    window.addEventListener('pointermove', onMove, { passive: true })
    window.addEventListener('blur', onBlur)
    window.addEventListener('focus', onFocus)
    return () => {
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('blur', onBlur)
      window.removeEventListener('focus', onFocus)
    }
  }, [])

  function onTypingKey() {
    const v = visit.current, now = performance.now()
    if (v.firstKeyAt == null) {
      v.firstKeyAt = now
      // reading up to the first key counts on the word the cursor rests on
      if (v.lastWord != null && v.lastMoveAt != null && now - v.lastMoveAt >= HOVER_MIN_MS) {
        const h = v.hover[v.lastWord] || (v.hover[v.lastWord] = { word: v.lastWord, dwell_ms: 0, hover_count: 0 })
        h.dwell_ms += Math.min(now - v.lastMoveAt, HOVER_CAP_MS)
        h.hover_count += 1
      }
    }
    v.lastKeyAt = now
    resetIdle()
  }

  function visitMetrics() {
    const v = visit.current
    const pause = v.firstKeyAt == null ? null : Math.max(0, v.firstKeyAt - v.shownAt - v.blurredMs)
    return {
      pre_typing_ms: pause,
      pre_typing_away: v.lostFocus || (pause != null && pause >= AWAY_MS),
      hover_words: Object.values(v.hover).map(h => ({ ...h, dwell_ms: Math.round(h.dwell_ms) })),
    }
  }

  useEffect(() => () => clearTimeout(idleTimer.current), [])

  function resetIdle() {
    clearTimeout(idleTimer.current)
    idleTimer.current = setTimeout(() => api.auditIdle(`Q${qi + 1} of ${total}`), IDLE_MS)
  }

  function updateResponse(value) {
    const next = [...responses]
    next[qi] = value
    setResponses(next)
    resetIdle()
  }

  function blockPaste(e) {
    e.preventDefault()
    setNotice('Please type your answer — pasting is turned off so we can measure typing.')
  }

  async function saveSnapshot() {
    try { await api.questionSnapshot(q, response, qi, total, visitMetrics()) } catch (_) { /* keep the client moving */ }
  }

  async function goPrevious() {
    if (qi === 0 || busy) return
    setBusy(true); await saveSnapshot(); setBusy(false)
    setQi(qi - 1)
  }

  async function goNext() {
    setBusy(true); await saveSnapshot(); setBusy(false)
    if (isLast) navigate('/assessment/done')
    else setQi(qi + 1)
  }

  wordRefs.current = []
  const nextLabel = trimmed === 0 ? (isLast ? 'Skip and finish' : 'Skip this question') : (isLast ? 'Finish' : 'Next question')

  return (
    <AssessmentShell step="writing" lost={lost}>
      <StepHeading kicker="Part 4 · Writing" title="Answer in your own words">
        Write a sentence or two. There are no right or wrong answers.
      </StepHeading>

      {/* Progress */}
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-semibold text-tsub" aria-live="polite">Question {qi + 1} of {total}</p>
        <p className="text-sm text-tsub">{responses.filter(r => r.trim()).length} answered</p>
      </div>
      <div className="flex gap-1 mb-6" aria-hidden="true">
        {QUESTIONS.map((_, i) => (
          <span key={i} className={`h-1.5 flex-1 rounded-full transition-colors ${i < qi ? 'bg-success' : i === qi ? 'bg-accent-ink' : 'bg-border'}`} />
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={qi} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.25, ease: EASE }}>
          <div className="bg-white rounded-3xl border border-border shadow-card p-8">
            <p className="text-2xl font-semibold leading-relaxed text-tmain text-center" id="prompt-text">
              {q.prompt.split(' ').map((word, wi) => (
                <span key={`${qi}-${wi}`} ref={el => { wordRefs.current[wi] = el }} data-word={word} className="mr-1.5 inline-block">{word}</span>
              ))}
            </p>
            <textarea
              ref={textareaRef}
              aria-labelledby="prompt-text"
              className="mt-6 w-full min-h-[200px] resize-none rounded-2xl border border-border bg-white px-5 py-4 text-lg leading-relaxed text-tmain outline-none focus:border-accent-ink focus:ring-4 focus:ring-accent/15"
              value={response}
              maxLength={800}
              onChange={e => { updateResponse(e.target.value); if (notice) setNotice('') }}
              onKeyDown={onTypingKey}
              onPaste={blockPaste}
              onDrop={blockPaste}
              spellCheck={false}
              autoComplete="off"
              placeholder="Type your answer here…"
            />
            <div className="mt-2 flex items-center justify-between text-sm">
              <span className="text-tsub flex items-center gap-1.5">
                {trimmed > 0 && trimmed < SHORT_ANSWER && (<><Lightbulb size={15} className="text-amber-ink" aria-hidden="true" /> A sentence or two works best.</>)}
                {trimmed >= SHORT_ANSWER && (<><Check size={15} className="text-success-ink" aria-hidden="true" /> Thank you.</>)}
              </span>
              <span className={response.length >= 750 ? 'text-coral-ink font-semibold' : 'text-tsub'}>{response.length}/800</span>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>

      {notice && <Alert tone="info" className="mt-4">{notice}</Alert>}

      <div className="mt-6 flex items-center justify-between gap-3">
        <Button variant="secondary" size="lg" icon={ArrowLeft} disabled={qi === 0 || busy} onClick={goPrevious}>Previous</Button>
        <Button size="lg" variant={trimmed === 0 ? 'secondary' : 'primary'} iconRight={ArrowRight} loading={busy} onClick={goNext}>
          {nextLabel}
        </Button>
      </div>
    </AssessmentShell>
  )
}
