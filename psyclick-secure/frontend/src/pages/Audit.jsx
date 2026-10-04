import { useEffect, useMemo, useState } from 'react'
import { ClipboardList, Search, X, ShieldCheck, ShieldAlert, RefreshCw } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { PageShell, Card, Button, Alert, Segmented, EmptyState, Skeleton } from '../components/ui.jsx'

const GROUPS = {
  all:      { label: 'All activity', match: () => true },
  staff:    { label: 'Staff',        match: a => ['clinician', 'admin', 'auditor'].includes(a) },
  client:   { label: 'Assessments',  match: a => a === 'patient' },
  security: { label: 'Security',     match: a => ['security', 'system'].includes(a) },
}
const ACTOR_LABEL = { clinician: 'Clinician', admin: 'Administrator', auditor: 'Auditor', patient: 'Client session', security: 'Security', system: 'System' }
const ACTOR_TONE  = { patient: 'bg-[#5BA4CF]/15 text-[#2F6690]', security: 'bg-coral/10 text-coral-ink', system: 'bg-black/[0.05] text-tmain' }
const PAGE = 100
const POLL_MS = 30_000

// Audit times are recorded in the computer's local time
function formatLocal(ts) {
  const d = new Date(String(ts).replace(' ', 'T'))
  return isNaN(d) ? String(ts) : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'medium' })
}

export default function Audit() {
  const [logs, setLogs]       = useState(null)
  const [group, setGroup]     = useState('all')
  const [query, setQuery]     = useState('')
  const [shown, setShown]     = useState(PAGE)
  const [check, setCheck]     = useState(null)
  const [checking, setChecking] = useState(false)
  const [err, setErr]         = useState('')

  useEffect(() => {
    let cancelled = false
    const load = () => api.auditLogs('').then(d => {
      if (cancelled) return
      if (Array.isArray(d)) { setLogs(d); setErr('') } else { setLogs(l => l || []); setErr(d?.error || 'The audit log could not be loaded.') }
    })
    load()
    const t = setInterval(() => { if (document.visibilityState === 'visible') load() }, POLL_MS)
    return () => { cancelled = true; clearInterval(t) }
  }, [])

  useEffect(() => { setShown(PAGE) }, [group, query])

  async function verify() {
    setChecking(true)
    const res = await api.verifyAudit()
    setChecking(false)
    setCheck(res)
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (logs || []).filter(l => GROUPS[group].match(l.actor) &&
      (!q || `${l.action} ${l.detail || ''}`.toLowerCase().includes(q)))
  }, [logs, group, query])

  const counts = useMemo(() => Object.fromEntries(Object.entries(GROUPS).map(([k, g]) => [k, (logs || []).filter(l => g.match(l.actor)).length])), [logs])

  return (
    <PageShell
      eyebrow="Administration"
      title="Audit log"
      subtitle="Every sign-in, assessment step and change is recorded in a tamper-evident chain."
      actions={<Button variant="secondary" icon={ShieldCheck} loading={checking} onClick={verify}>Verify integrity</Button>}
    >
      {check && (check.valid ? (
        <Alert tone="success" className="mb-5" title="The audit log is intact" onClose={() => setCheck(null)}>
          {check.checked} entries checked — none have been changed or removed.
        </Alert>
      ) : check.error ? (
        <Alert tone="error" className="mb-5" onClose={() => setCheck(null)}>{check.error}</Alert>
      ) : (
        <Alert tone="error" className="mb-5" title="The audit chain is broken" onClose={() => setCheck(null)}>
          Entry #{check.first_invalid_log_id} does not match its recorded fingerprint. Someone may have edited the database — report this to your administrator.
        </Alert>
      ))}
      {err && <Alert tone="error" className="mb-5">{err}</Alert>}

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <Segmented ariaLabel="Activity type" value={group} onChange={setGroup}
          options={Object.entries(GROUPS).map(([value, g]) => ({ value, label: g.label, count: logs ? counts[value] : undefined }))} />
        <div className="relative flex-1 min-w-[220px] max-w-sm">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-tsub" aria-hidden="true" />
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search actions or details" aria-label="Search the audit log"
            className="w-full h-11 pl-11 pr-10 rounded-xl border border-border bg-white outline-none focus:border-accent-ink focus:ring-4 focus:ring-accent/15" />
          {query && <button onClick={() => setQuery('')} aria-label="Clear search" className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-tsub hover:text-tmain cursor-pointer"><X size={16} aria-hidden="true" /></button>}
        </div>
        <p className="text-sm text-tsub flex items-center gap-1.5"><RefreshCw size={14} aria-hidden="true" /> Updates every 30 seconds</p>
      </div>

      <Card className="overflow-hidden">
        {logs === null ? (
          <div className="p-6 space-y-2">{[0, 1, 2, 3, 4].map(i => <Skeleton key={i} className="h-11" />)}</div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={ClipboardList} title={logs.length ? 'No entries match' : 'No activity recorded yet'}>
            {logs.length ? 'Try a different search or activity type.' : 'Entries appear as soon as people use PsyClick.'}
          </EmptyState>
        ) : (
          <>
            <table className="w-full">
              <caption className="sr-only">Audit entries, newest first</caption>
              <thead>
                <tr className="text-left text-xs font-semibold uppercase tracking-wider text-tsub bg-[#F7FAFA]">
                  <th scope="col" className="px-6 py-3 w-[210px]">When</th>
                  <th scope="col" className="px-4 py-3 w-[160px]">Who</th>
                  <th scope="col" className="px-4 py-3">What happened</th>
                  <th scope="col" className="px-6 py-3">Details</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, shown).map((log, i) => {
                  const denied = /fail|denied|blocked/i.test(log.action)
                  return (
                    <tr key={i} className="border-t border-border/70 align-top">
                      <td className="px-6 py-3 text-sm text-tsub whitespace-nowrap tabular-nums">{formatLocal(log.timestamp)}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${ACTOR_TONE[log.actor] || 'bg-accent/10 text-accent-ink'}`}>
                          {ACTOR_LABEL[log.actor] || log.actor}
                        </span>
                      </td>
                      <td className={`px-4 py-3 font-medium ${denied ? 'text-coral-ink' : 'text-tmain'}`}>
                        <span className="inline-flex items-center gap-1.5">{denied && <ShieldAlert size={15} aria-hidden="true" />}{log.action}</span>
                      </td>
                      <td className="px-6 py-3 text-sm text-tsub break-words">{log.detail || '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            <div className="flex items-center justify-between px-6 py-4 border-t border-border text-sm text-tsub">
              <span>Showing {Math.min(shown, filtered.length)} of {filtered.length}</span>
              {shown < filtered.length && <Button variant="secondary" size="sm" onClick={() => setShown(s => s + PAGE)}>Show {Math.min(PAGE, filtered.length - shown)} more</Button>}
            </div>
          </>
        )}
      </Card>
    </PageShell>
  )
}
