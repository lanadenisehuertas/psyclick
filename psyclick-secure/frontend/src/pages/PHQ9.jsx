import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import AssessmentShell, { StepHeading, useStepStart } from '../components/AssessmentShell.jsx'
import Questionnaire from '../components/Questionnaire.jsx'
import { PHQ9_ITEMS } from '../lib/questionnaires.js'

const QUESTIONS = PHQ9_ITEMS

export default function PHQ9() {
  const navigate = useNavigate()
  const { setPhqScore } = useApp()
  const [busy, setBusy] = useState(false)
  const [err, setErr]   = useState('')

  // Start PHQ phase on mount so the mouse logger captures answer clicks
  const lost = useStepStart(api.phqStart)

  async function submit(answers) {
    const score = answers.reduce((s, a) => s + a, 0)
    setBusy(true); setErr('')
    // All nine answers go to the server: item 9 (self-harm) is surfaced to the
    // clinician in the report, never shown back to the client.
    const res = await api.phqSave(score, answers)
    setBusy(false)
    if (res?.success === false) { setErr(res.error || 'Your answers could not be saved. Please try again.'); return }
    setPhqScore(score)
    navigate('/assessment/gad7')
  }

  return (
    <AssessmentShell step="phq" lost={lost}>
      <StepHeading kicker="Part 3 · Questions 1 of 2" title="How have you been feeling?" />
      <Questionnaire
        stem={<>Over the <strong>last 2 weeks</strong>, how often have you been bothered by the following?</>}
        questions={QUESTIONS} onSubmit={submit} busy={busy} error={err} />
    </AssessmentShell>
  )
}
