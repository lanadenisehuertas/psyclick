import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine, Legend } from 'recharts'
import { ArrowLeft, Trash2, Plus, ArrowRight, ShieldAlert, TrendingUp, FileText } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { PageShell, Card, Button, Alert, Spinner, EmptyState, ConfirmDialog, Field, inputCls, useToast } from '../components/ui.jsx'
import PasswordDialog from '../components/PasswordDialog.jsx'
import { StatusBadge, flagMeta, formatTimestamp, parseTimestamp } from '../lib/status.jsx'

function phqLabel(s) {
  if (s == null) return '—'
  return s <= 4 ? 'Minimal' : s <= 9 ? 'Mild' : s <= 14 ? 'Moderate' : s <= 19 ? 'Moderately severe' : 'Severe'
}
function gadLabel(s) {
  if (s == null) return '—'
  return s <= 4 ? 'Minimal' : s <= 9 ? 'Mild' : s <= 14 ? 'Moderate' : 'Severe'
}
function change(curr, prev) {
  if (prev == null) return null
  return curr === prev ? 'Same as the previous session'
    : curr > prev ? `Up ${curr - prev} from the previous session` : `Down ${prev - curr} from the previous session`
}

export default function ClientDetail() {
  const { clientId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [sessions, setSessions]   = useState(null)
  const [err, setErr]             = useState('')
  const [askPwd, setAskPwd]       = useState(false)
  const [askDelete, setAskDelete] = useState(false)
  const [typed, setTyped]         = useState('')
  const [deleting, setDeleting]   = useState(false)

  useEffect(() => {
    if (!clientId) return
    api.clientSessions(clientId).then(data => {
      if (Array.isArray(data)) setSessions(data)
      else { setSessions([]); setErr(data?.error || 'Could not load this client.') }
    })
  }, [clientId])

  async function handleDelete() {
    setDeleting(true)
    const res = await api.deleteClient(clientId)
    setDeleting(false)
    if (res.success) {
      toast(`${clientId} and ${res.deleted} session${res.deleted !== 1 ? 's' : ''} were deleted.`)
      navigate('/clients')
    } else toast(res.error || 'The record could not be deleted.', 'error')
  }

  const list = sessions || []
  const latest = list[0]
  const prev = list[1]
  const anySafety = list.some(s => s.safety)
  const confirmMatches = typed.trim().toUpperCase() === (clientId || '').toUpperCase()
  const trend = [...list].reverse().map((s, i) => ({
    name: parseTimestamp(s.timestamp) ? formatTimestamp(s.timestamp, { month: 'short', day: 'numeric' }) : `#${i + 1}`,
    phq: s.phq, gad: s.gad,
  }))

  const back = (
    <button onClick={() => navigate('/clients')}
      className="inline-flex items-center gap-2 text-tsub hover:text-tmain font-medium mb-4 h-9 -ml-1 px-1 rounded-lg cursor-pointer">
      <ArrowLeft size={18} aria-hidden="true" /> All clients
    </button>
  )

  return (
    <PageShell
      back={back}
      eyebrow="Client"
      title={clientId}
      subtitle={sessions === null ? 'Loading…' : `${list.length} session${list.length !== 1 ? 's' : ''} on record${list.length ? ` · first seen ${formatTimestamp(list[list.length - 1].timestamp, { dateStyle: 'medium' })}` : ''}`}
      actions={<>
        <Button icon={Plus} onClick={() => navigate(`/intake?client=${encodeURIComponent(clientId)}`)}>New session for {clientId}</Button>
        <Button variant="danger" icon={Trash2} onClick={() => setAskPwd(true)} disabled={!list.length}>Delete record</Button>
      </>}
    >
      {sessions === null ? <Spinner label="Loading sessions…" /> : err ? <Alert tone="error">{err}</Alert> : list.length === 0 ? (
        <Card><EmptyState icon={FileText} title="No sessions for this client">Start an assessment to create their first session.</EmptyState></Card>
      ) : (
        <div className="space-y-6">
          {anySafety && (
            <Alert tone="error" title="This client answered PHQ-9 question 9 (thoughts of self-harm) above 0">
              Review the sessions marked with the shield icon and follow your safety protocol.
            </Alert>
          )}

          <div className="grid lg:grid-cols-3 gap-4">
            <Card className={`p-6 border-2 ${flagMeta(latest.flag, latest.label).soft}`}>
              <p className="text-sm font-semibold text-tsub uppercase tracking-wider">Latest result</p>
              <div className="mt-3"><StatusBadge flag={latest.flag} label={latest.label} size="lg" /></div>
              <p className="mt-3 text-tmain font-semibold">{flagMeta(latest.flag, latest.label).headline}</p>
              <p className="text-sm text-tsub mt-1">{formatTimestamp(latest.timestamp, { dateStyle: 'full', timeStyle: 'short' })}</p>
              <Button variant="secondary" size="sm" className="mt-4" iconRight={ArrowRight}
                onClick={() => navigate(`/clients/session/${latest.session_id}`)}>Open latest report</Button>
            </Card>
            <Card className="p-6">
              <p className="text-sm font-semibold text-tsub uppercase tracking-wider">Depression · PHQ-9</p>
              <p className="mt-2 text-4xl font-bold text-tmain tabular-nums">{latest.phq}<span className="text-lg text-tsub font-medium"> / 27</span></p>
              <p className="mt-1 font-semibold text-tmain">{phqLabel(latest.phq)}</p>
              {prev && <p className="text-sm text-tsub mt-1">{change(latest.phq, prev.phq)}</p>}
            </Card>
            <Card className="p-6">
              <p className="text-sm font-semibold text-tsub uppercase tracking-wider">Anxiety · GAD-7</p>
              <p className="mt-2 text-4xl font-bold text-tmain tabular-nums">{latest.gad}<span className="text-lg text-tsub font-medium"> / 21</span></p>
              <p className="mt-1 font-semibold text-tmain">{gadLabel(latest.gad)}</p>
              {prev && <p className="text-sm text-tsub mt-1">{change(latest.gad, prev.gad)}</p>}
            </Card>
          </div>

          <Card className="p-6">
            <h2 className="text-lg font-bold text-tmain flex items-center gap-2"><TrendingUp size={20} className="text-accent-ink" aria-hidden="true" /> Questionnaire scores over time</h2>
            {trend.length < 2 ? (
              <p className="text-tsub mt-2">A trend appears after the second session.</p>
            ) : (
              <div className="mt-4 h-[260px]" role="img" aria-label={`PHQ-9 and GAD-7 across ${trend.length} sessions`}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trend} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
                    <CartesianGrid stroke="#E8F0F0" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#557272' }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 27]} tick={{ fontSize: 12, fill: '#557272' }} axisLine={false} tickLine={false} />
                    <ReferenceLine y={10} stroke="#9A5B00" strokeDasharray="5 4"
                      label={{ value: 'Moderate (10)', position: 'insideTopLeft', fontSize: 11, fill: '#9A5B00' }} />
                    <Tooltip contentStyle={{ fontSize: 13, borderRadius: 12, border: '1px solid #E4F0F0' }} />
                    <Legend wrapperStyle={{ fontSize: 13 }} />
                    <Line type="monotone" dataKey="phq" name="PHQ-9" stroke="#087F7D" strokeWidth={2.5} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="gad" name="GAD-7" stroke="#2F6690" strokeWidth={2.5} dot={{ r: 4 }} strokeDasharray="6 3" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>

          <Card className="overflow-hidden">
            <div className="px-6 py-5 border-b border-border">
              <h2 className="text-lg font-bold text-tmain">Session history</h2>
              <p className="text-sm text-tsub">Newest first. Open any session for its full report.</p>
            </div>
            <ul className="divide-y divide-border">
              {list.map((s, i) => (
                <li key={s.session_id}>
                  <button onClick={() => navigate(`/clients/session/${s.session_id}`)}
                    className="w-full px-6 py-4 flex flex-wrap items-center gap-4 text-left hover:bg-[#F7FBFB] transition-colors cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-ink">
                    <span className="w-24 text-sm font-semibold text-tsub">Session {list.length - i}</span>
                    <span className="flex-1 min-w-[180px] text-tmain">{formatTimestamp(s.timestamp, { dateStyle: 'medium', timeStyle: 'short' })}</span>
                    <span className="text-sm text-tsub tabular-nums">PHQ-9 <strong className="text-tmain">{s.phq}</strong> · GAD-7 <strong className="text-tmain">{s.gad}</strong></span>
                    {s.safety && <ShieldAlert size={18} className="text-coral-ink" aria-label="Self-harm answer" />}
                    <StatusBadge flag={s.flag} label={s.label} />
                    <ArrowRight size={18} className="text-accent-ink" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}

      <PasswordDialog open={askPwd} onCancel={() => setAskPwd(false)}
        title="Confirm it's you" description="Deleting records needs your password." confirmLabel="Continue"
        onConfirm={() => { setAskPwd(false); setTyped(''); setAskDelete(true) }} />
      <ConfirmDialog open={askDelete} danger busy={deleting}
        title={`Permanently delete ${clientId}?`}
        description={`This removes ${list.length} session${list.length !== 1 ? 's' : ''} and cannot be undone. The deletion is written to the audit log.`}
        confirmLabel="Delete permanently" confirmDisabled={!confirmMatches}
        onCancel={() => setAskDelete(false)}
        onConfirm={() => { if (confirmMatches) handleDelete() }}>
        <Field label={`Type ${clientId} to confirm`} hint="This protects against deleting the wrong client."
          error={typed && !confirmMatches ? `That doesn't match ${clientId}.` : undefined}>
          {(p) => <input {...p} className={inputCls} value={typed} onChange={e => setTyped(e.target.value)} autoComplete="off" data-autofocus />}
        </Field>
      </ConfirmDialog>
    </PageShell>
  )
}
