import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { Check, LogOut, PlugZap } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import PasswordDialog from './PasswordDialog.jsx'
import { ConfirmDialog, Button, EASE } from './ui.jsx'

// Starts a step's recording on the server. If it is refused (PsyClick restarted,
// or the screen was opened without a consented session), report it so the
// client is not left typing into a session that records nothing.
export function useStepStart(startFn) {
  const [lost, setLost] = useState(false)
  useEffect(() => {
    let alive = true
    Promise.resolve(startFn?.()).then(res => { if (alive && res?.success === false) setLost(true) })
    return () => { alive = false }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
  return lost
}

// Client-facing steps, in plain words.
export const STEPS = [
  { key: 'typing',   label: 'Typing' },
  { key: 'clicking', label: 'Clicking' },
  { key: 'phq',      label: 'Questions 1' },
  { key: 'gad',      label: 'Questions 2' },
  { key: 'writing',  label: 'Writing' },
]

function Stepper({ current }) {
  const idx = STEPS.findIndex(s => s.key === current)
  return (
    <ol className="flex items-center gap-2" aria-label="Assessment progress">
      {STEPS.map((s, i) => {
        const done = i < idx, active = i === idx
        return (
          <li key={s.key} className="flex items-center gap-2" aria-current={active ? 'step' : undefined}>
            <span className={`flex items-center gap-2 rounded-full pl-1 pr-3 h-8 text-sm font-semibold transition-colors
              ${active ? 'bg-accent-ink text-white' : done ? 'bg-success/15 text-success-ink' : 'bg-white/70 text-tsub border border-border'}`}>
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs
                ${active ? 'bg-white/20' : done ? 'bg-success text-white' : 'bg-bg'}`} aria-hidden="true">
                {done ? <Check size={13} strokeWidth={3} /> : i + 1}
              </span>
              <span className="hidden md:inline">{s.label}</span>
              <span className="sr-only">{done ? ' — done' : active ? ' — current step' : ''}</span>
            </span>
            {i < STEPS.length - 1 && <span className={`w-4 h-0.5 rounded ${i < idx ? 'bg-success' : 'bg-border'}`} aria-hidden="true" />}
          </li>
        )
      })}
    </ol>
  )
}

export default function AssessmentShell({ step, children, width = 'max-w-3xl', lost = false }) {
  const navigate = useNavigate()
  const { setClient, setReport } = useApp()
  const [askPwd, setAskPwd] = useState(false)
  const [askEnd, setAskEnd] = useState(false)
  const [askRestart, setAskRestart] = useState(false)

  function endSession() {
    api.auditLog('clinician', 'Ended assessment early', 'Session discarded')
    setAskEnd(false)
    setReport(null)
    setClient(null)
    navigate('/dashboard')
  }

  return (
    <div className="h-screen overflow-y-auto assessment-bg">
      <header className="sticky top-0 z-30 backdrop-blur-md bg-[#F3F7F9]/80 border-b border-border/70">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <img src={`${import.meta.env.BASE_URL}images/LOGOggg.png`} alt="" className="w-8 h-8 object-contain" />
            <span className="font-bold text-tmain hidden sm:inline">PsyClick</span>
          </div>
          {step && <Stepper current={step} />}
          <button onClick={() => setAskPwd(true)}
            className="inline-flex items-center gap-2 h-9 px-3 rounded-lg text-sm font-medium text-tsub hover:text-tmain hover:bg-black/[0.04] cursor-pointer">
            <LogOut size={16} aria-hidden="true" /> <span className="hidden sm:inline">End session</span>
          </button>
        </div>
      </header>
      <motion.main key={step} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, ease: EASE }}
        className={`${width} mx-auto px-6 py-10`}>
        {lost ? (
          <div className="min-h-[60vh] flex flex-col items-center justify-center text-center" role="alert">
            <span className="w-16 h-16 rounded-2xl bg-amber/20 text-amber-ink flex items-center justify-center"><PlugZap size={32} aria-hidden="true" /></span>
            <h1 className="mt-6 text-3xl font-bold text-tmain">This session isn't active</h1>
            <p className="mt-3 text-lg text-tsub max-w-[48ch]">
              Nothing is being recorded right now — PsyClick may have restarted. Please let your clinician know.
            </p>
            <Button size="lg" className="mt-8" onClick={() => setAskRestart(true)}>Clinician: set up again</Button>
          </div>
        ) : children}
      </motion.main>

      <PasswordDialog open={askPwd} onCancel={() => setAskPwd(false)}
        title="End this session?" description="For the clinician only. Enter your password to stop the assessment."
        onConfirm={() => { setAskPwd(false); setAskEnd(true) }} />
      <PasswordDialog open={askRestart} onCancel={() => setAskRestart(false)}
        title="Set up the session again" description="Enter your password to return to the session set-up."
        onConfirm={() => { setAskRestart(false); navigate('/intake') }} />
      <ConfirmDialog open={askEnd} danger
        title="Stop without saving?"
        description="The answers from this session will not be saved. You can start a new assessment for this client at any time."
        confirmLabel="Stop and discard" cancelLabel="Keep going"
        onCancel={() => setAskEnd(false)} onConfirm={endSession} />
    </div>
  )
}

// Shared heading for each client-facing step
export function StepHeading({ kicker, title, children }) {
  return (
    <div className="text-center mb-8">
      {kicker && <p className="text-sm font-semibold uppercase tracking-[0.16em] text-accent-ink mb-2">{kicker}</p>}
      <h1 className="text-[34px] leading-tight font-bold text-tmain">{title}</h1>
      {children && <p className="text-lg text-tsub mt-2 max-w-[56ch] mx-auto leading-relaxed">{children}</p>}
    </div>
  )
}
