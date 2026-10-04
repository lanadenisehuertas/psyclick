import { useCallback, useEffect, useState } from 'react'
import { ArchiveRestore, CheckCircle2, Fingerprint, KeyRound, Plus, RefreshCw, ShieldCheck, UserCog, XCircle, Check, Copy } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import { PageShell, Card, Button, Alert, IconTile, Modal, ConfirmDialog, Field, PasswordInput, inputCls, Skeleton, useToast } from '../components/ui.jsx'

const ROLES = [
  { value: 'clinician', label: 'Clinician', text: 'Runs assessments and sees their own clients.' },
  { value: 'auditor',   label: 'Auditor',   text: 'Reads the audit log only. No client data.' },
  { value: 'admin',     label: 'Administrator', text: 'Everything, including accounts and backups.' },
]
const ROLE_LABEL = Object.fromEntries(ROLES.map(r => [r.value, r.label]))

function Metric({ icon, tone, label, value, detail }) {
  return (
    <Card className="p-5">
      <IconTile icon={icon} tone={tone} />
      <p className="mt-4 text-2xl font-bold text-tmain">{value}</p>
      <p className="font-semibold text-tmain">{label}</p>
      <p className="text-sm text-tsub mt-0.5">{detail}</p>
    </Card>
  )
}

function rules(pwd) {
  return [
    { ok: pwd.length >= 12, label: 'At least 12 characters' },
    { ok: /[A-Za-z]/.test(pwd), label: 'Contains a letter' },
    { ok: /\d/.test(pwd), label: 'Contains a number' },
  ]
}

export default function SecurityCenter() {
  const { user: me } = useApp()
  const toast = useToast()
  const [status, setStatus]   = useState(null)
  const [users, setUsers]     = useState(null)
  const [busy, setBusy]       = useState(false)
  const [backupMsg, setBackupMsg] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm]       = useState({ name: '', password: '', role: 'clinician' })
  const [formErr, setFormErr] = useState({})
  const [created, setCreated] = useState(null)
  const [pending, setPending] = useState(null)   // { user, patch, title, description, danger }
  const [copied, setCopied]   = useState(false)

  const refresh = useCallback(async () => {
    const [security, accountRows] = await Promise.all([api.securityStatus(), api.users()])
    setStatus(security?.audit ? security : null)
    setUsers(Array.isArray(accountRows) ? accountRows : [])
  }, [])
  useEffect(() => { refresh() }, [refresh])

  async function createAccount(e) {
    e.preventDefault()
    const fe = {}
    if (!form.name.trim()) fe.name = 'Enter the person’s full name.'
    if (!rules(form.password).every(r => r.ok)) fe.password = 'The temporary password must meet all three rules.'
    setFormErr(fe)
    if (Object.keys(fe).length) return
    setBusy(true)
    const result = await api.register(form.name.trim(), form.password, form.role)
    setBusy(false)
    if (result.success) {
      setShowCreate(false)
      setCreated({ id: result.clinician_id, name: form.name.trim(), role: result.role })
      setForm({ name: '', password: '', role: 'clinician' })
      refresh()
    } else setFormErr({ form: result.error || 'The account could not be created.' })
  }

  async function applyPending() {
    const { user, patch } = pending
    setBusy(true)
    const result = await api.updateUser(user.id, patch.role || user.role, patch.status || user.status)
    setBusy(false)
    setPending(null)
    if (result.success) { toast(`Access updated for ${user.name}.`); refresh() }
    else toast(result.error || 'The change could not be saved.', 'error')
  }

  async function createAndVerifyBackup() {
    setBusy(true); setBackupMsg({ tone: 'info', text: 'Creating an encrypted backup…' })
    const made = await api.createBackup()
    if (!made.success) { setBackupMsg({ tone: 'error', text: made.error || 'The backup could not be created.' }); setBusy(false); return }
    setBackupMsg({ tone: 'info', text: 'Checking the backup can be restored…' })
    const verified = await api.verifyBackup(made.file, made.sha256)
    setBackupMsg(verified.success
      ? { tone: 'success', text: `Backup created and verified. Fingerprint ${made.sha256.slice(0, 12)}…` }
      : { tone: 'error', text: verified.error || 'The backup was created but failed verification.' })
    setBusy(false); refresh()
  }

  const auditOk = status?.audit?.valid
  const backup = status?.latest_backup

  return (
    <PageShell
      eyebrow="Administration"
      title="Security center"
      subtitle="Manage who can sign in, check the audit trail and keep a tested backup."
      actions={<>
        <Button variant="secondary" icon={RefreshCw} onClick={refresh}>Refresh</Button>
        <Button icon={Plus} onClick={() => { setFormErr({}); setShowCreate(true) }}>Add account</Button>
      </>}
    >
      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {status === null && users === null ? [0, 1, 2, 3].map(i => <Skeleton key={i} className="h-[160px]" />) : <>
          <Metric icon={auditOk ? CheckCircle2 : XCircle} tone={auditOk ? 'green' : 'coral'} label="Audit trail"
            value={auditOk ? 'Intact' : 'Needs attention'} detail={`${status?.audit?.checked ?? 0} entries checked`} />
          <Metric icon={ArchiveRestore} tone={backup?.status === 'verified' ? 'green' : 'amber'} label="Latest backup"
            value={backup?.status === 'verified' ? 'Verified' : backup ? 'Not verified' : 'None yet'} detail={backup?.created_at || 'Create the first backup below'} />
          <Metric icon={UserCog} tone="teal" label="Active accounts" value={status?.active_users ?? '—'} detail="Named people who can sign in" />
          <Metric icon={Fingerprint} tone="blue" label="Signed in now" value={status?.active_sessions ?? '—'} detail="Signed out after 15 min idle" />
        </>}
      </div>

      <div className="grid xl:grid-cols-[1fr_340px] gap-5 mt-6 items-start">
        <Card className="overflow-hidden">
          <div className="px-6 py-5 border-b border-border">
            <h2 className="text-lg font-bold text-tmain">Accounts</h2>
            <p className="text-sm text-tsub">Changes take effect immediately and are written to the audit log.</p>
          </div>
          {users === null ? <div className="p-6 space-y-2">{[0, 1, 2].map(i => <Skeleton key={i} className="h-14" />)}</div> : (
            <ul className="divide-y divide-border">
              {users.map(u => {
                const self = String(u.id) === String(me?.id)
                const active = u.status === 'active'
                return (
                  <li key={u.id} className="px-6 py-4 flex flex-wrap items-center gap-4">
                    <span className="w-10 h-10 rounded-full bg-accent/10 text-accent-ink font-bold flex items-center justify-center flex-shrink-0" aria-hidden="true">
                      {u.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
                    </span>
                    <div className="flex-1 min-w-[160px]">
                      <p className="font-semibold text-tmain">{u.name}{self && <span className="text-tsub font-normal"> (you)</span>}</p>
                      <p className="text-sm text-tsub">ID {u.id} · last sign-in {u.last_login_at ? new Date(u.last_login_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'never'}</p>
                    </div>
                    <label className="sr-only" htmlFor={`role-${u.id}`}>Role for {u.name}</label>
                    <select id={`role-${u.id}`} value={u.role} disabled={busy || self}
                      onChange={e => setPending({ user: u, patch: { role: e.target.value },
                        title: `Make ${u.name} ${/^[aeiou]/i.test(ROLE_LABEL[e.target.value]) ? 'an' : 'a'} ${ROLE_LABEL[e.target.value]}?`,
                        description: ROLES.find(r => r.value === e.target.value)?.text })}
                      className="h-10 rounded-xl border border-border bg-white px-3 text-sm text-tmain cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed">
                      {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                    </select>
                    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${active ? 'bg-success/15 text-success-ink' : 'bg-coral/10 text-coral-ink'}`}>
                      {active ? <Check size={13} aria-hidden="true" /> : <XCircle size={13} aria-hidden="true" />}{active ? 'Active' : 'Disabled'}
                    </span>
                    <Button size="sm" variant={active ? 'danger' : 'secondary'} disabled={busy || self}
                      title={self ? 'You cannot disable your own account' : undefined}
                      onClick={() => setPending({ user: u, patch: { status: active ? 'disabled' : 'active' }, danger: active,
                        title: active ? `Disable ${u.name}?` : `Enable ${u.name}?`,
                        description: active ? 'They will be signed out and unable to sign in until re-enabled. Their records are kept.' : 'They will be able to sign in again.' })}>
                      {active ? 'Disable' : 'Enable'}
                    </Button>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>

        <aside className="space-y-5">
          <Card className="p-6">
            <IconTile icon={ArchiveRestore} tone="teal" />
            <h2 className="text-lg font-bold text-tmain mt-4">Encrypted backup</h2>
            <p className="text-sm text-tsub mt-1">Makes an encrypted copy of all data, then proves it can be restored.</p>
            {backupMsg && <Alert tone={backupMsg.tone} className="mt-4">{backupMsg.text}</Alert>}
            <Button className="w-full mt-5" icon={ShieldCheck} loading={busy && backupMsg?.tone === 'info'} disabled={busy} onClick={createAndVerifyBackup}>
              Create and verify backup
            </Button>
          </Card>
          <Card className="p-6">
            <h3 className="font-bold text-tmain flex items-center gap-2"><KeyRound size={18} className="text-accent-ink" aria-hidden="true" /> Protections in place</h3>
            <ul className="mt-3 space-y-2 text-sm text-tmain">
              {['Passwords stored with scrypt hashing', 'Account locks for 15 min after 5 wrong passwords', 'Automatic sign-out after 15 min idle', 'Role and ownership checked on the server', 'Consent required before any recording'].map(t => (
                <li key={t} className="flex gap-2"><Check size={16} className="text-success-ink flex-shrink-0 mt-0.5" aria-hidden="true" />{t}</li>
              ))}
            </ul>
          </Card>
        </aside>
      </div>

      {/* Create account */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add an account" description="The person signs in with the ID shown after you create the account." width="max-w-lg">
        <form onSubmit={createAccount} noValidate className="space-y-5">
          {formErr.form && <Alert tone="error">{formErr.form}</Alert>}
          <Field label="Full name" error={formErr.name} required>
            {(p) => <input {...p} className={inputCls} value={form.name} data-autofocus autoComplete="off"
              onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. Dr. Ana Reyes" />}
          </Field>
          <Field label="Temporary password" error={formErr.password} hint="Share it privately. They can sign in with it straight away." required>
            {(p) => <PasswordInput {...p} autoComplete="new-password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />}
          </Field>
          <ul className="-mt-2 space-y-1" aria-label="Password rules">
            {rules(form.password).map(r => (
              <li key={r.label} className={`text-sm flex items-center gap-2 ${r.ok ? 'text-success-ink' : 'text-tsub'}`}>
                <Check size={14} className={r.ok ? '' : 'opacity-30'} aria-hidden="true" />{r.label}
              </li>
            ))}
          </ul>
          <fieldset>
            <legend className="text-sm font-semibold text-tmain mb-2">Role</legend>
            <div className="grid gap-2">
              {ROLES.map(r => (
                <label key={r.value} className={`flex items-start gap-3 rounded-xl border p-3 cursor-pointer ${form.role === r.value ? 'border-accent-ink bg-accent/5' : 'border-border hover:border-accent/50'}`}>
                  <input type="radio" name="role" value={r.value} checked={form.role === r.value} onChange={() => setForm({ ...form, role: r.value })} className="mt-1 accent-[#087F7D]" />
                  <span><span className="font-semibold text-tmain block">{r.label}</span><span className="text-sm text-tsub">{r.text}</span></span>
                </label>
              ))}
            </div>
          </fieldset>
          <div className="flex gap-3 pt-1">
            <Button type="button" variant="secondary" className="flex-1" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" className="flex-1" loading={busy}>Create account</Button>
          </div>
        </form>
      </Modal>

      {/* Created: hand over the ID */}
      <Modal open={!!created} onClose={() => setCreated(null)} title="Account created"
        description={created ? `Give ${created.name} this ID and the temporary password.` : ''}>
        <div className="rounded-2xl border-2 border-dashed border-accent/50 p-6 text-center">
          <p className="text-sm font-semibold text-tsub uppercase tracking-wider">Clinician ID</p>
          <p className="text-5xl font-bold text-tmain tracking-wider mt-2 tabular-nums">{created?.id}</p>
          <p className="text-sm text-tsub mt-2">{ROLE_LABEL[created?.role]}</p>
          <Button variant="secondary" size="sm" className="mt-4" icon={copied ? Check : Copy}
            onClick={async () => { try { await navigator.clipboard.writeText(String(created.id)); setCopied(true); setTimeout(() => setCopied(false), 2000) } catch (_) {} }}>
            {copied ? 'Copied' : 'Copy ID'}
          </Button>
        </div>
        <Button className="w-full mt-6" onClick={() => setCreated(null)} data-autofocus>Done</Button>
      </Modal>

      <ConfirmDialog open={!!pending} danger={pending?.danger} busy={busy}
        title={pending?.title || ''} description={pending?.description}
        confirmLabel="Yes, change it" onCancel={() => setPending(null)} onConfirm={applyPending} />
    </PageShell>
  )
}
