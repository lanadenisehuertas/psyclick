import { useState } from 'react'
import { EyeOff, Eye, Lock } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { FREQUENCY_OPTIONS } from '../components/Questionnaire.jsx'
import { PHQ9_ITEMS, GAD7_ITEMS } from '../lib/questionnaires.js'

const LABEL = Object.fromEntries(FREQUENCY_OPTIONS.map(o => [o.value, o.label]))
const TONE = ['text-tsub', 'text-tmain', 'text-amber-ink font-semibold', 'text-coral-ink font-semibold']

function AnswerTable({ title, items, answers }) {
  return (
    <div>
      <p className="text-xs font-semibold text-tsub uppercase tracking-wide mb-2">{title}</p>
      <ol className="divide-y divide-[#E3ECEF] border border-[#E3ECEF] rounded-xl overflow-hidden">
        {items.map((text, i) => (
          <li key={i} className="flex items-start gap-3 px-3 py-2 text-sm bg-white">
            <span className="font-mono text-tsub w-5 flex-shrink-0">{i + 1}</span>
            <span className="flex-1 text-tmain">{text}</span>
            <span className={`whitespace-nowrap ${TONE[answers[i]] || 'text-tsub'}`}>{LABEL[answers[i]] ?? '—'} ({answers[i]})</span>
          </li>
        ))}
      </ol>
    </div>
  )
}

// The client's item-by-item answers. They are stored with the session but
// shown only when the clinician who ran it asks; each viewing is audited.
// They stay out of the printed report unless revealed first.
export function QuestionnaireAnswers({ sessionId, stored }) {
  const [state, setState] = useState({ status: 'hidden' })

  async function reveal() {
    setState({ status: 'loading' })
    try {
      const res = await api.sessionAnswers(sessionId)
      setState({ status: 'shown', phq: res.phq, gad: res.gad })
    } catch (e) {
      setState({ status: 'error', error: e.message || 'Could not load the answers.' })
    }
  }

  const shown = state.status === 'shown'
  const none = shown && !state.phq && !state.gad
  return (
    <div className="surface p-6 print-avoid" {...(shown ? {} : { 'data-print-hide': true })}>
      <div className="flex items-start gap-4">
        <span className="w-10 h-10 rounded-full border border-[#D9E6EA] text-[#0A6B80] flex items-center justify-center flex-shrink-0">
          <Lock size={18} aria-hidden="true" />
        </span>
        <div className="flex-1 min-w-0">
          <p className="font-display font-semibold text-[#0F2A33]">Questionnaire answers (private)</p>
          <p className="text-sm text-tsub mt-0.5 max-w-[72ch]">
            The client's answer to each PHQ-9 and GAD-7 question. Only you can open them, and each viewing is recorded in the audit log.
          </p>
        </div>
        <div data-print-hide>
          {shown ? (
            <button type="button" onClick={() => setState({ status: 'hidden' })}
              className="btn-ghost text-sm inline-flex items-center gap-1.5"><EyeOff size={16} aria-hidden="true" /> Hide</button>
          ) : (
            <button type="button" onClick={reveal} disabled={state.status === 'loading' || stored === false}
              className="btn-ghost text-sm inline-flex items-center gap-1.5"><Eye size={16} aria-hidden="true" />
              {state.status === 'loading' ? 'Opening…' : 'Show answers'}</button>
          )}
        </div>
      </div>
      {stored === false && <p className="text-sm text-tsub mt-3">This session was recorded before item answers were kept; only the totals exist.</p>}
      {state.status === 'error' && <p className="text-sm text-coral-ink mt-3">{state.error}</p>}
      {none && <p className="text-sm text-tsub mt-3">No item answers were stored for this session; only the totals exist.</p>}
      {shown && !none && (
        <div className="grid lg:grid-cols-2 print:grid-cols-2 gap-4 mt-4">
          {state.phq && <AnswerTable title="PHQ-9 · depression" items={PHQ9_ITEMS} answers={state.phq} />}
          {state.gad && <AnswerTable title="GAD-7 · anxiety" items={GAD7_ITEMS} answers={state.gad} />}
        </div>
      )}
    </div>
  )
}
