import { useState } from 'react'
import { Lock, X } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'

export default function PasswordDialog({ onConfirm, onCancel }) {
  const { user } = useApp()
  const [pwd,  setPwd]  = useState('')
  const [err,  setErr]  = useState('')
  const [busy, setBusy] = useState(false)

  async function handleConfirm() {
    if (!pwd) { setErr('Please enter your password.'); return }
    if (!user?.id) { setErr('Clinician session invalid. Please log in again.'); return }
    setBusy(true)
    try {
      const res = await api.verifyClinician(user.id, pwd)
      setBusy(false)
      if (res.success) {
        onConfirm()
      } else {
        setErr(res.error || 'Incorrect password.');
        setPwd('')
      }
    } catch (err) {
      setBusy(false)
      setErr('Verification failed. Check your connection.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-[24px] shadow-modal w-[400px] p-8 animate-slide-up">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="w-14 h-14 rounded-full bg-accent/10 flex items-center justify-center">
            <Lock className="text-accent" size={24} />
          </div>
          <button onClick={onCancel} className="text-tsub hover:text-tmain transition-colors">
            <X size={20} />
          </button>
        </div>

        <h2 className="text-lg font-bold text-tmain mb-1">Clinician Verification</h2>
        <p className="text-sm text-tsub mb-6">Enter your clinician password to continue.</p>

        <input
          type="password"
          value={pwd}
          onChange={e => { setPwd(e.target.value); setErr('') }}
          onKeyDown={e => e.key === 'Enter' && handleConfirm()}
          placeholder="Clinician password"
          className="input-field mb-2"
          autoFocus
        />
        {err && <p className="text-coral text-sm mb-3">{err}</p>}

        <div className="flex gap-3 mt-4">
          <button onClick={onCancel}    className="btn-ghost flex-1">Cancel</button>
          <button onClick={handleConfirm} disabled={busy}
                  className="btn-primary flex-1 disabled:opacity-60">
            {busy ? 'Verifying…' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  )
}
