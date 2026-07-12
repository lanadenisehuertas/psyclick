import { useCallback, useEffect, useState } from 'react'
import {
  ArchiveRestore, CheckCircle2, Fingerprint, KeyRound, Plus,
  RefreshCw, ShieldCheck, UserCog, XCircle,
} from 'lucide-react'
import Sidebar from '../components/Sidebar.jsx'
import { api } from '../api/psyclick.js'

function Metric({ icon: Icon, label, value, tone = 'accent', detail }) {
  const tones = {
    accent: 'bg-accent/10 text-adark', success: 'bg-success/10 text-success',
    amber: 'bg-amber/10 text-amber', coral: 'bg-coral/10 text-coral',
  }
  return (
    <div className="card p-5 animate-fade-up-1">
      <div className={`w-10 h-10 rounded-2xl grid place-items-center ${tones[tone]}`}><Icon size={19} /></div>
      <p className="mt-4 text-[11px] uppercase tracking-[0.18em] text-tsub font-bold">{label}</p>
      <p className="mt-1 text-2xl font-bold text-tmain">{value}</p>
      <p className="mt-1 text-xs text-tsub leading-relaxed">{detail}</p>
    </div>
  )
}

export default function SecurityCenter() {
  const [status, setStatus] = useState(null)
  const [users, setUsers] = useState([])
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', password: '', role: 'clinician' })

  const refresh = useCallback(async () => {
    const [security, accountRows] = await Promise.all([api.securityStatus(), api.users()])
    setStatus(security?.audit ? security : null)
    setUsers(Array.isArray(accountRows) ? accountRows : [])
  }, [])

  useEffect(() => { refresh() }, [refresh])

  async function createAccount(e) {
    e.preventDefault(); setBusy(true); setNotice('')
    const result = await api.register(form.name, form.password, form.role)
    if (result.success) {
      setNotice(`Account ${result.clinician_id} created with ${result.role} access.`)
      setForm({ name: '', password: '', role: 'clinician' }); setShowCreate(false); await refresh()
    } else setNotice(result.error || 'Account creation failed.')
    setBusy(false)
  }

  async function updateAccount(user, patch) {
    setBusy(true); setNotice('')
    const result = await api.updateUser(user.id, patch.role || user.role, patch.status || user.status)
    setNotice(result.success ? `Access updated for ${user.name}.` : result.error || 'Update failed.')
    if (result.success) await refresh()
    setBusy(false)
  }

  async function createAndVerifyBackup() {
    setBusy(true); setNotice('Creating encrypted backup…')
    const created = await api.createBackup()
    if (!created.success) { setNotice(created.error || 'Backup failed.'); setBusy(false); return }
    const verified = await api.verifyBackup(created.file, created.sha256)
    setNotice(verified.success
      ? `Encrypted backup verified. SHA-256 ${created.sha256.slice(0, 16)}…`
      : verified.error || 'Backup verification failed.')
    await refresh(); setBusy(false)
  }

  const auditOk = status?.audit?.valid
  const backup = status?.latest_backup

  return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <header className="relative overflow-hidden bg-sidebar text-white px-8 pt-8 pb-16">
          <div className="absolute -right-20 -top-24 w-80 h-80 rounded-full border border-accent/20" />
          <div className="absolute right-16 top-10 w-32 h-32 rounded-full bg-accent/10 blur-2xl" />
          <div className="relative flex items-start justify-between gap-8">
            <div>
              <p className="text-accent text-[11px] uppercase tracking-[0.22em] font-bold">Administrative trust boundary</p>
              <h1 className="mt-2 text-3xl font-bold tracking-tight">Security Center</h1>
              <p className="mt-2 text-[#8AB6B6] text-sm max-w-xl">Manage least-privilege access, verify the audit chain, and produce a tested encrypted recovery point.</p>
            </div>
            <button onClick={refresh} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-[#B8D3D3] hover:bg-white/5 flex items-center gap-2">
              <RefreshCw size={15} /> Refresh evidence
            </button>
          </div>
        </header>

        <div className="px-8 pb-10 -mt-8 relative">
          <section className="grid grid-cols-4 gap-4">
            <Metric icon={auditOk ? CheckCircle2 : XCircle} label="Audit integrity" value={auditOk ? 'Verified' : 'Attention'} tone={auditOk ? 'success' : 'coral'} detail={`${status?.audit?.checked ?? 0} chained events checked`} />
            <Metric icon={ArchiveRestore} label="Recovery point" value={backup?.status === 'verified' ? 'Verified' : backup ? 'Created' : 'None'} tone={backup?.status === 'verified' ? 'success' : 'amber'} detail={backup?.created_at || 'Create the first encrypted backup'} />
            <Metric icon={UserCog} label="Active users" value={status?.active_users ?? '—'} detail="Unique named accounts" />
            <Metric icon={Fingerprint} label="Active sessions" value={status?.active_sessions ?? '—'} detail="15-minute idle timeout" />
          </section>

          {notice && <div className="mt-5 rounded-2xl border border-accent/20 bg-white px-5 py-3 text-sm text-tmain shadow-card">{notice}</div>}

          <section className="grid grid-cols-[1fr_300px] gap-5 mt-5">
            <div className="card overflow-hidden animate-fade-up-2">
              <div className="px-6 py-5 border-b border-border flex items-center justify-between">
                <div><h2 className="font-bold text-tmain">Account access registry</h2><p className="text-xs text-tsub mt-1">Role and lifecycle changes are written to the audit chain.</p></div>
                <button onClick={() => setShowCreate(true)} className="bg-accent hover:bg-adark text-white rounded-xl px-4 py-2.5 text-sm font-semibold flex items-center gap-2"><Plus size={15} /> Add account</button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="bg-[#F7FAFA] text-[10px] uppercase tracking-widest text-tsub">
                    {['Identity', 'Role', 'Status', 'Last login', 'Control'].map(h => <th key={h} className="px-5 py-3 text-left">{h}</th>)}
                  </tr></thead>
                  <tbody>
                    {users.map(user => <tr key={user.id} className="border-t border-border/70">
                      <td className="px-5 py-4"><p className="font-semibold text-tmain">{user.name}</p><p className="text-[11px] text-tsub">ID {user.id}</p></td>
                      <td className="px-5 py-4"><select value={user.role} disabled={busy} onChange={e => updateAccount(user, { role: e.target.value })} className="bg-bg border border-border rounded-lg px-2.5 py-2 text-xs text-tmain"><option value="admin">Admin</option><option value="clinician">Clinician</option><option value="auditor">Auditor</option></select></td>
                      <td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${user.status === 'active' ? 'bg-success/10 text-success' : 'bg-coral/10 text-coral'}`}>{user.status}</span></td>
                      <td className="px-5 py-4 text-xs text-tsub">{user.last_login_at || 'Never'}</td>
                      <td className="px-5 py-4"><button disabled={busy} onClick={() => updateAccount(user, { status: user.status === 'active' ? 'disabled' : 'active' })} className="text-xs font-semibold text-adark hover:underline">{user.status === 'active' ? 'Disable' : 'Enable'}</button></td>
                    </tr>)}
                  </tbody>
                </table>
              </div>
            </div>

            <aside className="space-y-5 animate-fade-up-3">
              <div className="card p-6 bg-sidebar text-white border-0">
                <div className="w-11 h-11 rounded-2xl bg-accent/15 text-accent grid place-items-center"><ArchiveRestore size={20} /></div>
                <h2 className="font-bold mt-4">Verified recovery</h2>
                <p className="text-xs text-[#8AB6B6] mt-2 leading-relaxed">Creates a transaction-consistent SQLite copy, protects it with Windows DPAPI, checks SHA-256, decrypts only in a temporary directory, and runs SQLite integrity_check.</p>
                <button disabled={busy} onClick={createAndVerifyBackup} className="mt-5 w-full rounded-xl bg-accent hover:bg-adark disabled:opacity-60 py-3 text-sm font-bold flex items-center justify-center gap-2"><ShieldCheck size={16} /> Create & verify</button>
              </div>
              <div className="card p-5">
                <div className="flex items-center gap-3"><KeyRound size={18} className="text-adark" /><h3 className="font-bold text-tmain text-sm">Enforced policy</h3></div>
                <ul className="mt-4 space-y-2 text-xs text-tsub leading-relaxed"><li>• scrypt password hashing</li><li>• 5-attempt / 15-minute lockout</li><li>• 15-minute session inactivity limit</li><li>• server-side role and ownership checks</li><li>• consent required before capture</li></ul>
              </div>
            </aside>
          </section>
        </div>
      </main>

      {showCreate && <div className="fixed inset-0 bg-sidebar/55 backdrop-blur-sm z-50 grid place-items-center p-6">
        <form onSubmit={createAccount} className="w-full max-w-md bg-white rounded-[24px] shadow-modal p-7 animate-slide-up">
          <p className="text-[10px] uppercase tracking-[0.2em] text-adark font-bold">Administrator provisioning</p>
          <h2 className="text-xl font-bold text-tmain mt-2">Create named account</h2>
          <div className="mt-6 space-y-4">
            <input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Full name" className="input-field w-full" />
            <input required type="password" minLength={12} value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder="12+ character temporary password" className="input-field w-full" />
            <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} className="input-field w-full"><option value="clinician">Clinician</option><option value="auditor">Auditor</option><option value="admin">Administrator</option></select>
          </div>
          <div className="flex gap-3 mt-6"><button type="button" onClick={() => setShowCreate(false)} className="flex-1 rounded-xl border border-border py-3 text-sm font-semibold text-tsub">Cancel</button><button disabled={busy} className="flex-1 rounded-xl bg-accent text-white py-3 text-sm font-bold">Create account</button></div>
        </form>
      </div>}
    </div>
  )
}
