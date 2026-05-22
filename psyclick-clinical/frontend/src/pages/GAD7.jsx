import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import StageBar from '../components/StageBar.jsx'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import AnimatedBackground from '../components/AnimatedBackground.jsx'

const QUESTIONS = [
  'Feeling nervous, anxious, or on edge',
  'Not being able to stop or control worrying',
  'Worrying too much about different things',
  'Trouble relaxing',
  'Being so restless that it is hard to sit still',
  'Becoming easily annoyed or irritable',
  'Feeling afraid, as if something awful might happen',
]

const OPTIONS = [
  { label: 'Not at all',          value: 0 },
  { label: 'Several days',        value: 1 },
  { label: 'More than half days', value: 2 },
  { label: 'Nearly every day',    value: 3 },
]

export default function GAD7() {
  const navigate = useNavigate()
  const { setGadScore } = useApp()
  const [answers, setAnswers] = useState(Array(QUESTIONS.length).fill(null))
  const [busy,    setBusy]    = useState(false)
  const [err,     setErr]     = useState('')

  const allAnswered = answers.every(a => a !== null)
  const score = answers.reduce((s, a) => s + (a ?? 0), 0)

  function setAnswer(qi, val) {
    const next = [...answers]
    next[qi] = val
    setAnswers(next)
  }

  async function handleSubmit() {
    if (!allAnswered) { setErr('Please answer all questions before continuing.'); return }
    setErr('')
    setBusy(true)
    await api.gadStart()
    await api.gadSave(score)
    setBusy(false)
    setGadScore(score)
    navigate('/assessment/emotional')
  }

  const answered = answers.filter(a => a !== null).length

  return (
    <div className="h-screen overflow-y-auto assessment-bg">
    <AnimatedBackground />
    <div className="task-shell" style={{ position: 'relative', zIndex: 1 }}>
      {/* Logo top */}
      <img src={`${import.meta.env.BASE_URL}images/LOGOggg.png`} alt="PsyClick" className="task-logo" />

      <div className="w-full max-w-6xl">
        <div className="mb-2">
          <button
            onClick={() => navigate('/intake')}
            className="flex items-center gap-1.5 text-tsub hover:text-tmain text-sm transition-colors"
          >
            <ArrowLeft size={15} /> Back
          </button>
        </div>
        <StageBar active={1} />

        <h1 className="task-title">GAD-7</h1>
        <p className="task-subtitle mb-8">
          Over the last 2 weeks, how often have you been bothered by the following problems?
        </p>

        <div className="space-y-4 mb-6">
          {QUESTIONS.map((q, qi) => (
            <div key={qi} className="card p-6">
              <p className="text-tmain text-lg font-semibold mb-5 text-center">
                <span className="text-tsub mr-2">{qi + 1}.</span>{q}
              </p>
              <div className="grid grid-cols-4 gap-3">
                {OPTIONS.map(opt => {
                  const selected = answers[qi] === opt.value
                  return (
                    <button
                      key={opt.value}
                      onClick={() => setAnswer(qi, opt.value)}
                      className={`rounded-xl py-4 px-3 text-sm font-semibold border transition-all duration-150 text-center ${
                        selected
                          ? 'bg-accent text-white border-accent shadow-sm scale-105'
                          : 'bg-white text-tmain border-border hover:border-accent/50 hover:bg-accent/5'
                      }`}
                    >
                      <span className="block text-2xl font-bold mb-1">{opt.value}</span>
                      {opt.label}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Progress only — no score/severity shown to client */}
        <div className="text-center text-tsub text-sm font-semibold mb-4">
          {answered} of {QUESTIONS.length} answered
        </div>

        {err && <p className="text-coral text-sm text-center mb-3">{err}</p>}

        <button
          onClick={handleSubmit}
          disabled={!allAnswered || busy}
          className="btn-primary w-full h-14 text-lg disabled:opacity-40 disabled:cursor-not-allowed mb-8"
        >
          {busy ? 'Saving…' : 'Continue →'}
        </button>
      </div>
    </div>
    </div>
  )
}
