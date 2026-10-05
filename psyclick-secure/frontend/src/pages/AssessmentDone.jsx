import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { Check, Lock, HeartHandshake, Loader2, RotateCcw } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import AssessmentShell from '../components/AssessmentShell.jsx'
import PasswordDialog from '../components/PasswordDialog.jsx'
import { Button, Alert, EASE } from '../components/ui.jsx'

// The end of the client's journey: a calm, positive close (peak-end), then a
// clinician-only unlock that processes and opens the report.
export default function AssessmentDone() {
  const navigate = useNavigate()
  const { setReport, setClient, client } = useApp()
  const [askPwd, setAskPwd] = useState(false)
  const [state, setState]   = useState('thanks')   // thanks | processing | error
  const [err, setErr]       = useState('')

  async function processResults() {
    setAskPwd(false); setState('processing'); setErr('')
    const res = await api.assessmentFinish()
    if (res.success && res.report) {
      setReport(res.report)
      setClient(null)
      navigate(res.report.session_id ? `/clients/session/${res.report.session_id}` : '/report', { replace: true })
    } else {
      setErr(res.error || 'The results could not be prepared.')
      setState('error')
    }
  }

  return (
    <AssessmentShell>
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-center">
        {state === 'thanks' && (
          <>
            <motion.span className="w-24 h-24 rounded-full bg-success text-white flex items-center justify-center shadow-lg"
              initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 220, damping: 16 }}>
              <Check size={48} strokeWidth={3} aria-hidden="true" />
            </motion.span>
            <motion.h1 className="mt-8 text-[40px] font-bold text-tmain leading-tight"
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15, duration: 0.4, ease: EASE }}>
              You're all done — thank you
            </motion.h1>
            <motion.p className="mt-3 text-xl text-tsub max-w-[46ch]"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
              Thank you for your time and honesty. Please hand the computer back to your clinician.
            </motion.p>
            <motion.div className="mt-10 flex items-center gap-3 rounded-2xl bg-white border border-border px-5 py-4 text-left shadow-card"
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}>
              <HeartHandshake size={26} className="text-accent-ink flex-shrink-0" aria-hidden="true" />
              <p className="text-tmain">Your answers are private. They are stored on this computer and copied to the clinic’s PsyClick cloud when online.</p>
            </motion.div>
            <div className="mt-12 pt-8 border-t border-border w-full max-w-md">
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-tsub">For the clinician</p>
              <Button size="lg" icon={Lock} className="mt-3 w-full" onClick={() => setAskPwd(true)}>
                Unlock and view results{client?.id ? ` for ${client.id}` : ''}
              </Button>
            </div>
          </>
        )}

        {state === 'processing' && (
          <div role="status" className="flex flex-col items-center">
            <Loader2 size={44} className="animate-spin text-accent-ink" aria-hidden="true" />
            <p className="mt-6 text-2xl font-bold text-tmain">Preparing the report…</p>
            <p className="mt-2 text-tsub">Analysing typing, mouse movement and answers. This takes a few seconds.</p>
          </div>
        )}

        {state === 'error' && (
          <div className="w-full max-w-lg">
            <Alert tone="error" title="The report could not be prepared">{err}</Alert>
            <div className="mt-6 flex justify-center gap-3">
              <Button variant="secondary" onClick={() => navigate('/dashboard')}>Back to dashboard</Button>
              <Button icon={RotateCcw} onClick={processResults}>Try again</Button>
            </div>
          </div>
        )}
      </div>

      <PasswordDialog open={askPwd} onCancel={() => setAskPwd(false)}
        title="Unlock the results" description="Enter your clinician password to analyse the session and open the report."
        confirmLabel="Unlock results" onConfirm={processResults} />
    </AssessmentShell>
  )
}
