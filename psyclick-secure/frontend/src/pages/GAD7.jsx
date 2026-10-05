import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import AssessmentShell, { StepHeading, useStepStart } from '../components/AssessmentShell.jsx'
import Questionnaire from '../components/Questionnaire.jsx'
import { GAD7_ITEMS } from '../lib/questionnaires.js'

const QUESTIONS = GAD7_ITEMS

export default function GAD7() {
  const navigate = useNavigate()
  const { setGadScore } = useApp()
  const [busy, setBusy] = useState(false)
  const [err, setErr]   = useState('')

  // Start GAD phase on mount so the mouse logger captures answer clicks
  const lost = useStepStart(api.gadStart)

  async function submit(answers) {
    const score = answers.reduce((s, a) => s + a, 0)
    setBusy(true); setErr('')
    const res = await api.gadSave(score, answers)
    setBusy(false)
    if (res?.success === false) { setErr(res.error || 'Your answers could not be saved. Please try again.'); return }
    setGadScore(score)
    navigate('/assessment/emotional')
  }

  return (
    <AssessmentShell step="gad" lost={lost}>
      <StepHeading kicker="Part 3 · Questions 2 of 2" title="A few more questions" />
      <Questionnaire
        stem={<>Over the <strong>last 2 weeks</strong>, how often have you been bothered by the following?</>}
        questions={QUESTIONS} onSubmit={submit} busy={busy} error={err} />
    </AssessmentShell>
  )
}
