import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ShieldCheck, ArrowLeft, Sparkles } from 'lucide-react'
import Sidebar from '../components/Sidebar.jsx'
import PasswordDialog from '../components/PasswordDialog.jsx'
import AnimatedBackground from '../components/AnimatedBackground.jsx'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'

export default function Intake() {
  const [name,        setName]        = useState('')
  const [sid,         setSid]         = useState('')
  const [consent,     setConsent]     = useState(false)
  const [showPwd,     setShowPwd]     = useState(false)
  const [pendingFn,   setPendingFn]   = useState(null)
  const [err,         setErr]         = useState('')
  const [genIdBusy,   setGenIdBusy]   = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [confirmData, setConfirmData] = useState(null)
  const { setClient, user } = useApp()
  const navigate = useNavigate()

  function guard(fn) { setPendingFn(() => fn); setShowPwd(true) }

  async function generateClientId() {
    setGenIdBusy(true)
    const res = await api.nextClientId(user?.id)
    setGenIdBusy(false)
    if (res.success) setSid(res.id)
    else setErr(res.error || 'Could not generate ID.')
  }

  async function handleSubmit() {
    const pidRaw = sid.trim()
    if (pidRaw && !/^C-\d{3}$/.test(pidRaw)) {
      setErr('Client ID must follow the format C-001 to C-100 (e.g. C-042).')
      return
    }
    const pid = pidRaw || name.trim() || 'C-UNKNOWN'
    const res = await api.intakeStart(pid, user?.id)
    if (!res.success) { setErr(res.error || 'Failed to start session.'); return }
    if (res.existing_sessions > 0) {
      setConfirmData({ pid, sessions: res.existing_sessions })
      setShowConfirm(true)
      return
    }
    proceedWithSession(pid)
  }

  function proceedWithSession(pid) {
    setClient({ id: pid })
    navigate('/calibration/keyboard')
  }

  return (
    <div className="h-screen flex bg-bg" style={{ position: 'relative' }}>
      <AnimatedBackground variant="subtle" />
      <Sidebar protected />
      <main className="flex-1 overflow-y-auto px-10 py-8 animate-fade-in" style={{ position: 'relative', zIndex: 1 }}>
        <button onClick={() => guard(() => navigate('/dashboard'))}
                className="flex items-center gap-2 text-tsub hover:text-tmain text-sm mb-6 transition-colors">
          <ArrowLeft size={16} /> Back to Dashboard
        </button>

        <h1 className="text-2xl font-bold text-tmain mb-1">New Client Intake</h1>
        <p className="text-tsub text-sm mb-8">Complete client information and establish biometric baseline.</p>

        <div className="max-w-4xl space-y-6">
          {/* Client info card */}
          <div className="card p-8">
            <h2 className="font-bold text-tmain text-lg mb-6">Client Information</h2>
            <div className="grid grid-cols-2 gap-5">
              <div>
                <label className="text-sm font-semibold text-tmain mb-2 block">Full Name</label>
                <input className="input-field" placeholder="Client's full name"
                       value={name} onChange={e => setName(e.target.value)} />
              </div>
              <div>
                <label className="text-sm font-semibold text-tmain mb-2 block">Client ID</label>
                <div className="flex gap-2">
                  <input className="input-field flex-1" placeholder="Use the format C-001, C-002..."
                         value={sid} onChange={e => setSid(e.target.value)} />
                  <button
                    type="button"
                    onClick={generateClientId}
                    disabled={genIdBusy}
                    title="Auto-assign next available client ID"
                    className="flex items-center gap-1.5 px-3 h-10 rounded-[10px] bg-accent/10 border border-accent/30
                               text-accent text-xs font-semibold hover:bg-accent/20 transition-all disabled:opacity-50 whitespace-nowrap"
                  >
                    <Sparkles size={13} />
                    {genIdBusy ? '…' : 'New ID'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Consent card */}
          <div className="card p-8">
            <div className="flex items-center gap-3 mb-3">
              <ShieldCheck className="text-accent" size={22} />
              <h2 className="font-bold text-tmain text-lg">Your Privacy Matters</h2>
            </div>
            <p className="text-tsub text-sm mb-5 leading-relaxed">
              I understand that my typing and mouse interaction data will be collected and analyzed
              for clinical assessment purposes. All data is encrypted and stored locally.
            </p>
            <label className="flex items-center gap-3 cursor-pointer group">
              <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)}
                     className="w-5 h-5 accent-accent rounded" />
              <span className="text-sm text-tmain group-hover:text-accent transition-colors">
                I consent to local biometric recording for this session
              </span>
            </label>
          </div>

          {err && <p className="text-coral text-sm">{err}</p>}

          <button
            disabled={!consent}
            onClick={() => guard(handleSubmit)}
            className="btn-primary w-full h-12 text-base disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Agree & Begin Baseline Calibration →
          </button>
        </div>
      </main>

      {showPwd && (
        <PasswordDialog
          onConfirm={() => { setShowPwd(false); pendingFn?.() }}
          onCancel={() => setShowPwd(false)}
        />
      )}

      {showConfirm && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-bg border border-border w-full max-w-md rounded-2xl p-8 shadow-2xl animate-scale-in">
            <h3 className="text-xl font-bold text-tmain mb-3">Returning Client</h3>
            <p className="text-tsub text-sm mb-8 leading-relaxed">
              Client <span className="text-tmain font-semibold">'{confirmData?.pid}'</span> already has {confirmData?.sessions} session(s) on record.
              <br/><br/>
              Do you want to start a new session for this client? (Existing data will be preserved.)
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 h-11 rounded-xl border border-border text-tsub font-semibold hover:bg-card transition-colors"
              >
                No, Go Back
              </button>
              <button
                onClick={() => { setShowConfirm(false); proceedWithSession(confirmData.pid) }}
                className="flex-1 h-11 rounded-xl bg-accent text-white font-semibold hover:bg-adark transition-colors shadow-lg shadow-accent/20"
              >
                Yes, Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
