import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Info } from 'lucide-react'
import { api } from '../api/psyclick.js'
import AssessmentShell, { StepHeading, useStepStart } from '../components/AssessmentShell.jsx'
import { Button, Alert } from '../components/ui.jsx'

const TARGET = 'Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce oxygen and energy in the form of sugar. This remarkable biochemical process occurs in the chloroplasts of plant cells.'

// Minimum completion before Continue is enabled (80%)
const MIN_PCT = 80

export default function KeyboardCalibration() {
  const [typed, setTyped]   = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy]     = useState(false)
  const [err, setErr]       = useState('')
  const navigate = useNavigate()
  const areaRef = useRef(null)

  const lost = useStepStart(api.kCalStart)

  async function handleNext() {
    setBusy(true); setErr('')
    const res = await api.kCalSave()
    setBusy(false)
    if (res?.success === false) {
      setErr(res.error || 'Something went wrong. Please try again.')
      if (res.retry) { setTyped(''); areaRef.current?.focus() }   // capture restarted on the server
      return
    }
    navigate('/calibration/mouse')
  }

  // Pasting or dropping text would skip the key presses we need to measure
  function blockPaste(e) {
    e.preventDefault()
    setNotice('Please type the text yourself — pasting is turned off for this task.')
  }

  const pct = Math.min(100, Math.round((typed.length / TARGET.length) * 100))
  const canContinue = pct >= MIN_PCT
  const doneUpTo = Math.min(typed.length, TARGET.length)

  return (
    <AssessmentShell step="typing" lost={lost}>
      <StepHeading kicker="Part 1 · Typing warm-up" title="Type the paragraph below">
        Type it as you normally would. Small mistakes are fine — no need to fix them.
      </StepHeading>

      <div className="bg-white rounded-2xl border border-border shadow-card p-6">
        <p className="text-sm font-semibold uppercase tracking-wider text-tsub mb-3">Copy this text</p>
        <p className="text-xl leading-relaxed text-tmain select-none" aria-label={TARGET}>
          <span className="text-[#9DB3B3]">{TARGET.slice(0, doneUpTo)}</span>
          <span className="bg-accent/15 rounded">{TARGET.slice(doneUpTo, doneUpTo + 1)}</span>
          <span>{TARGET.slice(doneUpTo + 1)}</span>
        </p>
      </div>

      <div className="mt-4 bg-white rounded-2xl border border-border shadow-card p-6">
        <label htmlFor="typing-area" className="text-sm font-semibold uppercase tracking-wider text-tsub">Type here</label>
        <textarea
          id="typing-area"
          ref={areaRef}
          className="mt-3 w-full min-h-[170px] resize-none rounded-xl border border-border bg-white px-4 py-3 text-lg leading-relaxed text-tmain outline-none focus:border-accent-ink focus:ring-4 focus:ring-accent/15"
          value={typed}
          onChange={e => { setTyped(e.target.value); if (notice) setNotice('') }}
          onPaste={blockPaste}
          onDrop={blockPaste}
          spellCheck={false}
          autoComplete="off"
          autoFocus
          placeholder="Start typing here…"
        />
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm font-semibold mb-2">
            <span className="text-tsub">{canContinue ? 'Great — you can continue whenever you are ready.' : `Type at least ${MIN_PCT}% to continue`}</span>
            <span className={canContinue ? 'text-success-ink' : 'text-accent-ink'}>{pct}%</span>
          </div>
          <div className="relative h-3 rounded-full bg-bg overflow-hidden" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Typing progress">
            <div className={`h-full rounded-full transition-[width] duration-300 ${canContinue ? 'bg-success' : 'bg-accent'}`} style={{ width: `${pct}%` }} />
            <span className="absolute top-0 h-full w-0.5 bg-tmain/30" style={{ left: `${MIN_PCT}%` }} aria-hidden="true" />
          </div>
        </div>
      </div>

      {notice && <Alert tone="info" className="mt-4">{notice}</Alert>}
      {err && <Alert tone="error" className="mt-4">{err}</Alert>}

      <div className="mt-8 flex justify-center">
        <Button size="lg" className="min-w-[260px]" iconRight={ArrowRight} disabled={!canContinue} loading={busy} onClick={handleNext}>
          Continue
        </Button>
      </div>
      {!canContinue && (
        <p className="mt-3 text-center text-sm text-tsub flex items-center justify-center gap-1.5">
          <Info size={14} aria-hidden="true" /> The button turns on at {MIN_PCT}%.
        </p>
      )}
    </AssessmentShell>
  )
}
