import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FlaskConical, CheckCircle, AlertTriangle,
  RefreshCw, Lock, Play, Users, BarChart2, Sparkles,
} from 'lucide-react'
import Sidebar from '../components/Sidebar.jsx'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'

const METRIC_LABELS = {
  t2_score:         'Hotelling T²',
  psi:              'Psychomotor Stress Index',
  pai:              'Psychomotor Anxiety Index',
  phq_score:        'PHQ-9',
  gad_score:        'GAD-7',
  flight_time_mean: 'Mean Flight Time (s)',
}

const TARGET = 100

export default function NormativeDashboard() {
  const navigate = useNavigate()
  const { user, setUser, setClient } = useApp()

  const [data,       setData]       = useState(null)
  const [computing,  setComputing]  = useState(false)
  const [adminPwd,   setAdminPwd]   = useState('')
  const [showAdmin,  setShowAdmin]  = useState(false)
  const [msg,        setMsg]        = useState('')

  // Tester session form
  const [testerId, setTesterId] = useState('')
  const [testerPwd, setTesterPwd] = useState('')
  const [testerErr, setTesterErr] = useState('')
  const [testerBusy, setTesterBusy] = useState(false)
  const [genIdBusy, setGenIdBusy] = useState(false)

  useEffect(() => { load() }, [])

  async function load() {
    const res = await api.normativeStats()
    setData(res)
  }

  async function generateTesterId() {
    setGenIdBusy(true)
    const res = await api.nextTesterId()
    setGenIdBusy(false)
    if (res.success) setTesterId(res.id)
    else setTesterErr(res.error || 'Could not generate Tester ID.')
  }

  // ── Start a normative session ─────────────────────────────────────────────
  async function handleStartSession() {
    setTesterErr('')
    if (!testerId.trim()) { setTesterErr('Please enter a Tester ID.'); return }
    if (!/^T-\d{3}$/.test(testerId.trim())) { setTesterErr('Tester ID must be in the format T-001 to T-100 (e.g. T-007).'); return }
    if (!testerPwd)       { setTesterErr('Please enter the tester password.'); return }
    setTesterBusy(true)
    const res = await api.normativeLogin(testerId.trim(), testerPwd)
    setTesterBusy(false)
    if (res.success) {
      setUser({ name: `Tester ${res.tester_id}`, id: res.tester_id, role: 'normer' })
      setClient({ id: res.tester_id, existing: 0 })
      navigate('/calibration/keyboard')
    } else {
      setTesterErr(res.error || 'Incorrect password.')
    }
  }

  // ── Compute baseline ──────────────────────────────────────────────────────
  async function handleCompute() {
    setMsg('')
    if (!user?.id) { setMsg('Please log in as a clinician first.'); return }
    setComputing(true)
    const res = await api.normativeCompute(user.id, adminPwd)
    setComputing(false)
    setShowAdmin(false)
    setAdminPwd('')
    if (res.success) {
      setMsg(`Baseline computed from ${res.count} sessions.`)
      load()
    } else {
      setMsg(res.error || 'Computation failed.')
    }
  }

  const count = data?.session_count ?? 0
  const ready = data?.baseline_ready ?? false
  const stats = data?.stats ?? {}
  const pct   = Math.min(100, Math.round((count / TARGET) * 100))

  return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 overflow-y-auto px-10 py-8 animate-fade-in">

        {/* Page header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center">
            <FlaskConical size={20} className="text-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-tmain">Normative Baseline</h1>
            <p className="text-tsub text-sm">Collect tester sessions and manage the population reference</p>
          </div>
        </div>

        <div className="max-w-5xl grid grid-cols-5 gap-5">

          {/* ── Left column: tester portal ──────────────────────────────── */}
          <div className="col-span-3 space-y-5">

            {/* Start a session card */}
            <div className="bg-white rounded-2xl border border-border shadow-card p-6">
              <div className="flex items-center gap-2 mb-1">
                <Play size={16} className="text-accent" />
                <h2 className="font-bold text-tmain text-sm uppercase tracking-wide">Start Normative Session</h2>
              </div>
              <p className="text-xs text-tsub mb-5 leading-relaxed">
                Normative testers enter their assigned ID and the session password below, then complete
                the full calibration + assessment procedure. Results are stored in the normative database.
              </p>

              <div className="space-y-3">
                <div>
                  <label className="text-xs font-semibold text-tmain mb-1.5 block">Tester ID</label>
                  <div className="flex gap-2">
                    <input
                      className="input-field flex-1"
                      placeholder="e.g. T-001"
                      value={testerId}
                      onChange={e => { setTesterId(e.target.value); setTesterErr('') }}
                      onKeyDown={e => e.key === 'Enter' && handleStartSession()}
                    />
                    <button
                      type="button"
                      onClick={generateTesterId}
                      disabled={genIdBusy}
                      title="Auto-assign next available Tester ID"
                      className="flex items-center gap-1.5 px-3 h-10 rounded-[10px] bg-accent/10 border border-accent/30
                                 text-accent text-xs font-semibold hover:bg-accent/20 transition-all disabled:opacity-50 whitespace-nowrap"
                    >
                      <Sparkles size={13} />
                      {genIdBusy ? '…' : 'Generate ID'}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-semibold text-tmain mb-1.5 block">Session Password</label>
                  <input
                    className="input-field"
                    type="password"
                    placeholder="Tester password"
                    value={testerPwd}
                    onChange={e => { setTesterPwd(e.target.value); setTesterErr('') }}
                    onKeyDown={e => e.key === 'Enter' && handleStartSession()}
                  />
                </div>
                {testerErr && <p className="text-coral text-xs">{testerErr}</p>}
                <button
                  onClick={handleStartSession}
                  disabled={testerBusy}
                  className="btn-primary w-full"
                >
                  <Play size={15} />
                  {testerBusy ? 'Starting…' : 'Begin Normative Session'}
                </button>
              </div>

              <div className="mt-5 pt-4 border-t border-border/50">
                <p className="text-xs text-tsub font-semibold mb-2">What testers will complete:</p>
                <div className="space-y-1.5">
                  {[
                    'Keyboard baseline calibration (~2 min)',
                    'Mouse baseline calibration (~2 min)',
                    'PHQ-9 depression screening',
                    'GAD-7 anxiety screening',
                    'Emotional response task — 11 prompts across 4 stressor domains (~10 min)',
                  ].map((s, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-tsub">
                      <span className="w-4 h-4 rounded-full bg-accent/10 text-accent text-[10px] font-bold flex items-center justify-center flex-shrink-0">
                        {i + 1}
                      </span>
                      {s}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Password info card */}
            <div className="bg-white rounded-2xl border border-border shadow-card p-5">
              <div className="flex items-center gap-2 mb-3">
                <Lock size={14} className="text-accent" />
                <h2 className="font-bold text-tmain text-sm uppercase tracking-wide">Tester Credentials</h2>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-tsub">Tester ID</span>
                  <span className="text-tmain font-medium">Assigned per tester (T-001 … T-100)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-tsub">Session Password</span>
                  <code className="font-mono bg-accent/10 text-accent px-2 py-0.5 rounded text-xs">NORMER123</code>
                </div>
              </div>
              <p className="text-xs text-tsub mt-3 leading-relaxed">
                Share this password with your 100 testers. Each tester uses their own unique ID so sessions
                can be tracked individually in the database.
              </p>
            </div>
          </div>

          {/* ── Right column: admin stats ────────────────────────────────── */}
          <div className="col-span-2 space-y-5">

            {/* Collection progress */}
            <div className="bg-white rounded-2xl border border-border shadow-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Users size={15} className="text-accent" />
                <h2 className="font-bold text-tmain text-sm uppercase tracking-wide">Collection</h2>
              </div>

              {/* Big counter */}
              <div className="text-center mb-4">
                <p className="text-5xl font-bold text-tmain leading-none">{count}</p>
                <p className="text-tsub text-sm mt-1">of {TARGET} sessions</p>
              </div>

              {/* Progress bar */}
              <div className="h-2.5 bg-border/30 rounded-full overflow-hidden mb-2">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${count >= TARGET ? 'bg-success' : 'bg-accent'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="text-xs text-tsub text-center">{pct}% complete</p>

              {/* Status badge */}
              <div className={`mt-4 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold ${
                ready ? 'bg-success/10 text-success' : count >= TARGET ? 'bg-amber/10 text-amber' : 'bg-border/40 text-tsub'
              }`}>
                {ready
                  ? <><CheckCircle size={13} /> Baseline Active</>
                  : count >= TARGET
                    ? <><AlertTriangle size={13} /> Ready to Compute</>
                    : <><FlaskConical size={13} /> Collecting Data</>
                }
              </div>
            </div>

            {/* Compute baseline */}
            <div className="bg-white rounded-2xl border border-border shadow-card p-5">
              <div className="flex items-center gap-2 mb-3">
                <BarChart2 size={15} className="text-accent" />
                <h2 className="font-bold text-tmain text-sm uppercase tracking-wide">Baseline</h2>
              </div>

              <p className="text-xs text-tsub leading-relaxed mb-4">
                {ready
                  ? `Active baseline computed from ${stats[Object.keys(stats)[0]]?.count ?? count} sessions. Re-compute to include new data.`
                  : count >= TARGET
                    ? 'Enough data collected. Enter your clinician password to lock in the baseline.'
                    : `Need ${TARGET - count} more session${TARGET - count !== 1 ? 's' : ''} before computing baseline.`
                }
              </p>

              {msg && (
                <p className={`text-xs mb-3 font-medium ${msg.includes('fail') || msg.includes('error') ? 'text-coral' : 'text-success'}`}>
                  {msg}
                </p>
              )}

              {!showAdmin ? (
                <button
                  onClick={() => setShowAdmin(true)}
                  disabled={count === 0}
                  className="btn-primary w-full text-sm disabled:opacity-40"
                >
                  <RefreshCw size={14} />
                  {ready ? 'Recompute' : 'Compute Baseline'}
                </button>
              ) : (
                <div className="space-y-2">
                  <input
                    className="input-field text-sm"
                    type="password"
                    placeholder="Clinician password"
                    value={adminPwd}
                    onChange={e => setAdminPwd(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleCompute()}
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <button onClick={handleCompute} disabled={computing} className="btn-primary flex-1 text-sm">
                      <Lock size={13} />
                      {computing ? 'Computing…' : 'Confirm'}
                    </button>
                    <button onClick={() => { setShowAdmin(false); setAdminPwd('') }}
                            className="btn-outline flex-1 text-sm h-10">
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Active stats table */}
            {ready && Object.keys(stats).length > 0 && (
              <div className="bg-white rounded-2xl border border-border shadow-card p-5">
                <p className="text-xs font-semibold text-tsub uppercase tracking-widest mb-3">Population Means</p>
                <div className="space-y-2">
                  {Object.entries(stats).map(([metric, s]) => (
                    <div key={metric} className="flex items-center justify-between text-sm">
                      <span className="text-tsub text-xs">{METRIC_LABELS[metric] || metric}</span>
                      <div className="text-right">
                        <span className="font-bold text-tmain font-mono">{Number(s.mean).toFixed(3)}</span>
                        <span className="text-tsub text-xs ml-1">±{Number(s.sd).toFixed(3)}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-tsub mt-3 pt-3 border-t border-border/50">
                  Updated: {stats[Object.keys(stats)[0]]?.computed_at?.slice(0, 16) ?? '—'}
                </p>
              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  )
}
