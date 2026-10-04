import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import AssessmentShell, { StepHeading, useStepStart } from '../components/AssessmentShell.jsx'
import Questionnaire from '../components/Questionnaire.jsx'

const QUESTIONS = [
  'Little interest or pleasure in doing things',
  'Feeling down, depressed, or hopeless',
  'Trouble falling or staying asleep, or sleeping too much',
  'Feeling tired or having little energy',
  'Poor appetite or overeating',
  'Feeling bad about yourself — or that you are a failure or have let yourself or your family down',
  'Trouble concentrating on things, such as reading the newspaper or watching television',
  'Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual',
  'Thoughts that you would be better off dead, or of hurting yourself in some way',
]

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
