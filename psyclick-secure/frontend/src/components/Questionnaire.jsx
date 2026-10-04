import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { Button, Alert, EASE } from './ui.jsx'

export const FREQUENCY_OPTIONS = [
  { value: 0, label: 'Not at all' },
  { value: 1, label: 'Several days' },
  { value: 2, label: 'More than half the days' },
  { value: 3, label: 'Nearly every day' },
]

// One question at a time; answering moves on automatically. Every answered
// question stays reachable through the numbered dots or the Back button.
export default function Questionnaire({ stem, questions, onSubmit, submitLabel = 'Continue', busy, error }) {
  const [answers, setAnswers] = useState(() => Array(questions.length).fill(null))
  const [qi, setQi]           = useState(0)
  const [dir, setDir]         = useState(1)
  const timer = useRef(null)
  useEffect(() => () => clearTimeout(timer.current), [])

  const answered = answers.filter(a => a !== null).length
  const allAnswered = answered === questions.length
  const isLast = qi === questions.length - 1

  function go(next) {
    clearTimeout(timer.current)
    setDir(next > qi ? 1 : -1)
    setQi(Math.max(0, Math.min(questions.length - 1, next)))
  }

  function choose(value) {
    const next = [...answers]
    next[qi] = value
    setAnswers(next)
    if (!isLast) timer.current = setTimeout(() => go(qi + 1), 380)
  }

  return (
    <div>
      <div className="bg-white/80 border border-border rounded-2xl px-5 py-4 text-center text-lg text-tmain">
        {stem}
      </div>

      {/* Progress: numbered dots, answered ones can be revisited */}
      <div className="mt-6 flex items-center justify-between gap-4">
        <p className="text-sm font-semibold text-tsub" aria-live="polite">Question {qi + 1} of {questions.length}</p>
        <ol className="flex gap-1.5" aria-label="Questions">
          {questions.map((_, i) => {
            const done = answers[i] !== null
            const reachable = done || i <= answered
            return (
              <li key={i}>
                <button onClick={() => reachable && go(i)} disabled={!reachable}
                  aria-label={`Question ${i + 1}${done ? ', answered' : ''}`} aria-current={i === qi ? 'step' : undefined}
                  className={`w-8 h-8 rounded-full text-xs font-bold flex items-center justify-center transition-colors
                    ${i === qi ? 'bg-accent-ink text-white ring-4 ring-accent/20' : done ? 'bg-success/15 text-success-ink hover:bg-success/25 cursor-pointer' : 'bg-white border border-border text-tsub'}
                    disabled:cursor-default`}>
                  {done && i !== qi ? <Check size={14} strokeWidth={3} aria-hidden="true" /> : i + 1}
                </button>
              </li>
            )
          })}
        </ol>
      </div>

      <div className="relative mt-4 min-h-[420px]">
        <AnimatePresence mode="wait" custom={dir}>
          <motion.fieldset key={qi} custom={dir}
            initial={{ opacity: 0, x: dir * 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: dir * -40 }}
            transition={{ duration: 0.25, ease: EASE }}
            className="bg-white rounded-3xl border border-border shadow-card p-7">
            <legend className="sr-only">Question {qi + 1}</legend>
            <p className="text-2xl font-semibold text-tmain leading-snug text-center max-w-[44ch] mx-auto">{questions[qi]}</p>
            <div role="radiogroup" aria-label={questions[qi]} className="mt-7 grid gap-3">
              {FREQUENCY_OPTIONS.map(opt => {
                const selected = answers[qi] === opt.value
                return (
                  <button key={opt.value} role="radio" aria-checked={selected} onClick={() => choose(opt.value)}
                    className={`w-full flex items-center gap-4 rounded-2xl border-2 px-5 h-[68px] text-left text-lg font-semibold cursor-pointer transition-colors
                      focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-ink
                      ${selected ? 'border-accent-ink bg-accent/10 text-tmain' : 'border-border bg-white text-tmain hover:border-accent/50 hover:bg-[#F5FBFB]'}`}>
                    <span className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0
                      ${selected ? 'border-accent-ink bg-accent-ink' : 'border-[#B7CCCC]'}`} aria-hidden="true">
                      {selected && <Check size={14} strokeWidth={3} className="text-white" />}
                    </span>
                    {opt.label}
                  </button>
                )
              })}
            </div>
          </motion.fieldset>
        </AnimatePresence>
      </div>

      {error && <Alert tone="error" className="mt-4">{error}</Alert>}

      <div className="mt-6 flex items-center justify-between gap-3">
        <Button variant="secondary" size="lg" icon={ArrowLeft} disabled={qi === 0} onClick={() => go(qi - 1)}>Back</Button>
        {isLast || allAnswered ? (
          <Button size="lg" iconRight={ArrowRight} disabled={!allAnswered} loading={busy} onClick={() => onSubmit(answers)}>
            {allAnswered ? submitLabel : `Answer all ${questions.length} to continue`}
          </Button>
        ) : (
          <Button size="lg" variant="secondary" iconRight={ArrowRight} disabled={answers[qi] === null} onClick={() => go(qi + 1)}>Next</Button>
        )}
      </div>
    </div>
  )
}
