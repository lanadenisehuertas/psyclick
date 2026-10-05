import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'motion/react'
import { ShieldCheck, RefreshCw, UserPlus, UserRound, Keyboard, MousePointerClick, ListChecks, PenLine, Search, ArrowRight, Check } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import { PageShell, Card, Button, Field, Alert, Segmented, ConfirmDialog, inputCls, EASE } from '../components/ui.jsx'
import { StatusBadge, formatTimestamp } from '../lib/status.jsx'

const PARTS = [
  { icon: Keyboard,          title: 'Typing warm-up',     text: 'Copy a short paragraph.', time: '2 min' },
  { icon: MousePointerClick, title: 'Clicking warm-up',   text: 'Click five circles in order.', time: '1 min' },
  { icon: ListChecks,        title: 'Two questionnaires', text: 'PHQ-9 and GAD-7, 16 questions.', time: '3 min' },
  { icon: PenLine,           title: 'Short written answers', text: '12 everyday questions.', time: '8–10 min' },
]

const RECORDED = [
  'Timing of key presses (not which words are typed)',
  'Mouse movement and clicks, including where the cursor rests while reading',
  'Questionnaire answers and scores',
  'Length of each written answer — the words themselves are not saved',
]

const ID_RE = /^C-\d{3}$/

// Optional context. It changes no score; the report uses it to say how far
// each comparison holds (the healthy reference group is adults aged 18–64).
const CONTEXT_CHOICES = [
  { key: 'age_band', label: 'Age group', options: [{ value: 'under18', label: 'Under 18' }, { value: '18-64', label: '18–64' }, { value: '65plus', label: '65 or older' }] },
  { key: 'keyboard', label: 'Keyboard used today', options: [{ value: 'desktop', label: 'Desktop' }, { value: 'laptop', label: 'Laptop' }, { value: 'other', label: 'Other' }] },
  { key: 'typing',   label: 'How often the client types', options: [{ value: 'daily', label: 'Every day' }, { value: 'sometimes', label: 'Sometimes' }, { value: 'rarely', label: 'Rarely' }] },
  { key: 'language', label: 'Language of the written answers', options: [{ value: 'english', label: 'English' }, { value: 'tagalog', label: 'Tagalog' }, { value: 'mixed', label: 'Both' }] },
]

function ChoiceRow({ label, options, value, onChange }) {
  return (
    <div role="radiogroup" aria-label={label}>
      <p className="text-sm font-semibold text-tmain mb-1.5">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map(o => {
          const on = value === o.value
          return (
            <button key={o.value} type="button" role="radio" aria-checked={on} onClick={() => onChange(on ? undefined : o.value)}
              className={`h-9 px-3.5 rounded-lg border text-sm font-semibold cursor-pointer transition-colors
                focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-ink
                ${on ? 'border-accent-ink bg-accent-ink text-white' : 'border-border bg-white text-tsub hover:text-tmain hover:border-accent/50'}`}>
              {o.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function Intake() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { setClient, user } = useApp()

  const preset = params.get('client') || ''
  const [kind, setKind]       = useState(preset ? 'returning' : 'new')
  const [newId, setNewId]     = useState('')
  const [idBusy, setIdBusy]   = useState(false)
  const [clients, setClients] = useState([])
  const [query, setQuery]     = useState('')
  const [picked, setPicked]   = useState(preset)
  const [consent, setConsent] = useState(false)
  const [busy, setBusy]       = useState(false)
  const [err, setErr]         = useState('')
  const [idErr, setIdErr]     = useState('')
  const [confirm, setConfirm] = useState(null)
  const [context, setContext] = useState({})

  async function suggestId() {
    setIdBusy(true)
    const res = await api.nextClientId(user?.id)
    setIdBusy(false)
    if (res.success) { setNewId(res.id); setIdErr('') }
    else setIdErr(res.error || 'Could not suggest a code. Type one in the format C-001.')
  }

  useEffect(() => { suggestId() }, [])                         // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { api.clients(user?.id).then(d => setClients(Array.isArray(d) ? d : [])) }, [user?.id])

  const filtered = useMemo(() => clients.filter(c => !query || c.id.toLowerCase().includes(query.trim().toLowerCase())), [clients, query])
  const clientId = kind === 'new' ? newId.trim().toUpperCase() : picked
  const idValid  = kind === 'new' ? ID_RE.test(clientId) : !!picked
  const blocker  = !idValid ? (kind === 'new' ? 'Enter a client code like C-001.' : 'Choose the returning client.')
                 : !consent ? 'Confirm the client has agreed to the recording.' : ''

  async function start(force = false) {
    if (kind === 'new' && !ID_RE.test(clientId)) { setIdErr('Use the format C- followed by three digits, e.g. C-007.'); return }
    if (blocker) return
    setErr(''); setBusy(true)
    const res = await api.intakeStart(clientId, user?.id, consent, '1.0', context)
    setBusy(false)
    if (!res.success) { setErr(res.error || 'The session could not be started. Please try again.'); return }
    if (!force && kind === 'new' && res.existing_sessions > 0) {
      setConfirm({ id: clientId, sessions: res.existing_sessions })
      return
    }
    setClient({ id: clientId, existing: res.existing_sessions })
    navigate('/assessment/welcome')
  }

  return (
    <PageShell
      eyebrow="New assessment"
      title="Set up the session"
      subtitle="Choose the client and record their consent. Then hand the computer to the client."
    >
      <div className="grid lg:grid-cols-[1fr_360px] gap-6 items-start">
        <div className="space-y-5">
          {/* 1 — Who */}
          <Card className="p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-display text-lg font-semibold text-tmain flex items-center gap-2"><span className="step-dot">1</span> Who is being assessed?</h2>
              <Segmented ariaLabel="Client type" value={kind} onChange={v => { setKind(v); setErr('') }}
                options={[{ value: 'new', label: 'New client', icon: UserPlus }, { value: 'returning', label: 'Returning client', icon: UserRound, count: clients.length }]} />
            </div>

            {kind === 'new' ? (
              <div className="mt-5 grid sm:grid-cols-[1fr_auto] gap-3 items-start">
                <Field label="Client code" error={idErr} hint="A code, never the client's name. PsyClick does not store names.">
                  {(p) => <input {...p} className={`${inputCls} font-semibold tracking-wide`} value={newId}
                    onChange={e => { setNewId(e.target.value); setIdErr('') }} placeholder="C-001" />}
                </Field>
                <Button variant="secondary" className="sm:mt-7" icon={RefreshCw} loading={idBusy} onClick={suggestId}>Suggest next</Button>
              </div>
            ) : (
              <div className="mt-5">
                {clients.length === 0 ? (
                  <Alert tone="info">No previous clients yet. Use <strong>New client</strong> for the first session.</Alert>
                ) : (
                  <>
                    <div className="relative">
                      <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-tsub" aria-hidden="true" />
                      <input className={`${inputCls} pl-11`} placeholder="Search by client code" value={query}
                        onChange={e => setQuery(e.target.value)} aria-label="Search clients" />
                    </div>
                    <div role="radiogroup" aria-label="Returning client" className="mt-3 grid sm:grid-cols-2 gap-2 max-h-[264px] overflow-y-auto pr-1">
                      {filtered.map(c => {
                        const on = picked === c.id
                        return (
                          <button key={c.id} role="radio" aria-checked={on} onClick={() => setPicked(c.id)}
                            className={`text-left rounded-xl border p-3.5 flex items-center gap-3 cursor-pointer transition-colors
                              focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-ink
                              ${on ? 'border-accent-ink bg-accent/5 ring-2 ring-accent/20' : 'border-border bg-white hover:border-accent/50'}`}>
                            <span className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${on ? 'border-accent-ink bg-accent-ink' : 'border-[#B7CCCC]'}`} aria-hidden="true">
                              {on && <Check size={12} strokeWidth={3} className="text-white" />}
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="block font-semibold text-tmain">{c.id}</span>
                              <span className="block text-xs text-tsub">{c.sessions} session{c.sessions !== 1 ? 's' : ''} · last {formatTimestamp(c.last_seen, { dateStyle: 'medium' })}</span>
                            </span>
                            {c.flag && <StatusBadge flag={c.flag} />}
                          </button>
                        )
                      })}
                      {filtered.length === 0 && <p className="text-sm text-tsub p-3">No client matches “{query}”.</p>}
                    </div>
                  </>
                )}
              </div>
            )}
          </Card>

          {/* 2 — Consent */}
          <Card className="p-6">
            <h2 className="font-display text-lg font-semibold text-tmain flex items-center gap-2"><span className="step-dot">2</span> Consent</h2>
            <p className="text-tsub mt-1.5">Read this to the client, or let them read it, before starting.</p>
            <div className="mt-4 rounded-xl bg-[#F5FAFA] border border-border p-4">
              <p className="font-semibold text-tmain flex items-center gap-2"><ShieldCheck size={18} className="text-accent-ink" aria-hidden="true" /> What PsyClick records</p>
              <ul className="mt-2 space-y-1.5">
                {RECORDED.map(r => (
                  <li key={r} className="flex gap-2 text-[15px] text-tmain"><Check size={16} className="text-success-ink flex-shrink-0 mt-1" aria-hidden="true" />{r}</li>
                ))}
              </ul>
              <p className="text-sm text-tsub mt-3">Everything is stored on this computer, and copied to the clinic's PsyClick cloud when online. The client can stop at any time.</p>
            </div>
            <label className={`mt-4 flex items-start gap-3 rounded-xl border p-4 cursor-pointer transition-colors ${consent ? 'border-success bg-success/5' : 'border-border hover:border-accent/50'}`}>
              <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)}
                className="mt-0.5 w-5 h-5 accent-[#087F7D] cursor-pointer" />
              <span className="text-[15px] text-tmain">
                <span className="font-semibold">The client understands and agrees</span> to this recording for today's session.
              </span>
            </label>
          </Card>

          {/* 3 — Context (optional) */}
          <Card className="p-6">
            <h2 className="font-display text-lg font-semibold text-tmain flex items-center gap-2"><span className="step-dot">3</span> About today <span className="text-sm font-medium text-tsub">(optional)</span></h2>
            <p className="text-tsub mt-1.5">Nothing here changes the scores. It tells the report how far each comparison applies to this client.</p>
            <div className="mt-4 grid sm:grid-cols-2 gap-x-6 gap-y-4">
              {CONTEXT_CHOICES.map(c => (
                <ChoiceRow key={c.key} label={c.label} options={c.options} value={context[c.key]}
                  onChange={v => setContext(x => { const n = { ...x }; if (v) n[c.key] = v; else delete n[c.key]; return n })} />
              ))}
            </div>
            <label className="mt-4 flex items-start gap-3 rounded-xl border border-border p-3.5 cursor-pointer hover:border-accent/50">
              <input type="checkbox" checked={!!context.condition}
                onChange={e => setContext(x => { const n = { ...x }; if (e.target.checked) n.condition = true; else delete n.condition; return n })}
                className="mt-0.5 w-5 h-5 accent-[#087F7D] cursor-pointer" />
              <span className="text-[15px] text-tmain">The client has a hand, arm, vision or other condition that affects typing or using a mouse.</span>
            </label>
          </Card>

          {err && <Alert tone="error">{err}</Alert>}

          <div className="flex flex-wrap items-center gap-4">
            <Button size="lg" iconRight={ArrowRight} loading={busy} disabled={!!blocker} onClick={() => start(false)}>
              Start assessment{idValid ? ` for ${clientId}` : ''}
            </Button>
            <Button variant="ghost" onClick={() => navigate('/dashboard')}>Cancel</Button>
            {blocker && <p className="text-sm text-tsub" aria-live="polite">{blocker}</p>}
          </div>
        </div>

        {/* What happens next */}
        <motion.aside initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.35, ease: EASE }}
          className="lg:sticky lg:top-6">
          <Card className="p-6">
            <p className="text-sm text-tsub">What the client will do</p>
            <p className="font-display text-2xl font-semibold text-tmain mt-0.5">About 15 minutes</p>
            <ol className="mt-5 space-y-4">
              {PARTS.map((p, i) => (
                <li key={p.title} className="flex gap-3">
                  <span className="font-mono text-lg font-semibold text-accent-ink w-6 flex-shrink-0" aria-hidden="true">{i + 1}</span>
                  <div className="flex-1">
                    <p className="font-semibold text-tmain flex justify-between gap-2">{p.title}<span className="text-sm font-medium text-tsub">{p.time}</span></p>
                    <p className="text-sm text-tsub">{p.text}</p>
                  </div>
                </li>
              ))}
            </ol>
            <p className="mt-5 text-sm text-tsub border-t border-border pt-4">
              Results stay locked until you enter your password at the end.
            </p>
          </Card>
        </motion.aside>
      </div>

      <ConfirmDialog
        open={!!confirm}
        title={`${confirm?.id} already has ${confirm?.sessions} session${confirm?.sessions !== 1 ? 's' : ''}`}
        description="Add today's session to this existing client? Their earlier results are kept. If this is someone else, go back and use a different code."
        confirmLabel="Yes, same client"
        cancelLabel="Use a different code"
        onCancel={() => { setConfirm(null); suggestId() }}
        onConfirm={() => { setConfirm(null); setClient({ id: confirm.id }); navigate('/assessment/welcome') }}
      />
    </PageShell>
  )
}
