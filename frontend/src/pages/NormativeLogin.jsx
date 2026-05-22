import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { FlaskConical, Sparkles } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'

export default function NormativeLogin() {
  const [testerId,    setTesterId]    = useState('')
  const [pwd,         setPwd]         = useState('')
  const [err,         setErr]         = useState('')
  const [busy,        setBusy]        = useState(false)
  const [genIdBusy,   setGenIdBusy]   = useState(false)
  const { setUser, setClient } = useApp()
  const navigate = useNavigate()

  async function generateTesterId() {
    setGenIdBusy(true)
    const res = await api.nextTesterId()
    setGenIdBusy(false)
    if (res.success) setTesterId(res.id)
    else setErr(res.error || 'Could not generate Tester ID.')
  }

  async function handleLogin() {
    setErr('')
    if (!testerId.trim()) { setErr('Please enter a Tester ID.'); return }
    if (!/^T-\d{3}$/.test(testerId.trim())) { setErr('Tester ID must follow the format T-001 to T-100 (e.g. T-007).'); return }
    if (!pwd) { setErr('Please enter the tester password.'); return }
    setBusy(true)
    const res = await api.normativeLogin(testerId.trim(), pwd)
    setBusy(false)
    if (res.success) {
      setUser({ name: `Tester ${res.tester_id}`, role: 'normer' })
      setClient({ id: res.tester_id, existing: 0 })
      navigate('/calibration/keyboard')
    } else {
      setErr(res.error || 'Login failed.')
    }
  }

  return (
    <div className="h-screen flex overflow-hidden animate-fade-in">
      {/* Left panel */}
      <div className="w-[420px] flex-shrink-0 bg-[#2D5F5F] flex flex-col items-center justify-center px-10 relative">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-white/15 flex items-center justify-center mx-auto mb-6">
            <FlaskConical size={32} className="text-white" />
          </div>
          <h1 className="text-white text-2xl font-bold mb-2">Normative Testing</h1>
          <p className="text-white/70 text-sm leading-relaxed">
            This portal is for normative baseline testers only.<br />
            Your session data contributes to the population reference for clinical comparisons.
          </p>
          <div className="mt-8 space-y-2 text-left">
            {[
              'Complete calibration + emotional task',
              'Takes approximately 15–20 minutes',
              'No clinical interpretation provided',
            ].map(f => (
              <div key={f} className="flex items-center gap-3 text-white/65 text-sm">
                <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-xs">✓</span>
                </div>
                {f}
              </div>
            ))}
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-[#1A4040]" />
      </div>

      {/* Right form */}
      <div className="flex-1 bg-bg flex items-center justify-center px-16">
        <div className="w-full max-w-[400px] animate-slide-up">
          <h2 className="text-3xl font-bold text-tmain mb-1">Tester Portal</h2>
          <p className="text-tsub text-base mb-8">Enter your assigned Tester ID and the session password</p>

          <div className="bg-white rounded-card shadow-card p-8 border border-border">
            <div className="mb-5">
              <label className="text-sm font-semibold text-tmain mb-2 block">Tester ID</label>
              <div className="flex gap-2">
                <input
                  className="input-field flex-1"
                  placeholder="Enter tester ID (e.g. T-001)"
                  value={testerId}
                  onChange={e => { setTesterId(e.target.value); setErr('') }}
                  onKeyDown={e => e.key === 'Enter' && handleLogin()}
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
            <div className="mb-4">
              <label className="text-sm font-semibold text-tmain mb-2 block">Session Password</label>
              <input
                className="input-field"
                type="password"
                placeholder="Enter the tester password"
                value={pwd}
                onChange={e => { setPwd(e.target.value); setErr('') }}
                onKeyDown={e => e.key === 'Enter' && handleLogin()}
              />
            </div>

            {err && <p className="text-coral text-sm mb-4">{err}</p>}

            <button onClick={handleLogin} disabled={busy} className="btn-primary w-full text-base mb-4">
              {busy ? 'Starting session…' : 'Begin Normative Session →'}
            </button>

            <Link to="/" className="block text-center text-xs text-tsub hover:text-accent transition-colors mt-2">
              ← Back to Clinician Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
