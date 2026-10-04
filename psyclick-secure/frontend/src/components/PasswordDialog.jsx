import { useState } from 'react'
import { Lock } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import { Modal, Button, Field, PasswordInput } from './ui.jsx'

// Clinician re-verification before leaving the client-facing part of the app.
export default function PasswordDialog({ onConfirm, onCancel, open = true,
  title = 'Clinician check', description = 'Enter your password to continue.', confirmLabel = 'Continue' }) {
  const { user } = useApp()
  const [pwd,  setPwd]  = useState('')
  const [err,  setErr]  = useState('')
  const [busy, setBusy] = useState(false)

  async function handleConfirm(e) {
    e?.preventDefault()
    if (!pwd) { setErr('Enter your password.'); return }
    if (!user?.id) { setErr('Your sign-in has ended. Please sign in again.'); return }
    setBusy(true)
    const res = await api.verifyClinician(user.id, pwd)
    setBusy(false)
    if (res.success) { setPwd(''); onConfirm() }
    else { setErr('That password is not correct.'); setPwd('') }
  }

  return (
    <Modal open={open} onClose={onCancel} title={title} description={description}>
      <form onSubmit={handleConfirm} noValidate>
        <div className="flex items-center gap-3 rounded-xl bg-[#F5FAFA] border border-border p-3 mb-4">
          <span className="w-9 h-9 rounded-lg bg-accent/10 text-accent-ink flex items-center justify-center" aria-hidden="true"><Lock size={18} /></span>
          <p className="text-sm text-tmain"><span className="font-semibold">{user?.name}</span> <span className="text-tsub">· ID {user?.id}</span></p>
        </div>
        <Field label="Password" error={err}>
          {(p) => <PasswordInput {...p} data-autofocus autoComplete="current-password" value={pwd}
            onChange={e => { setPwd(e.target.value); setErr('') }} />}
        </Field>
        <div className="flex gap-3 mt-6">
          <Button type="button" variant="secondary" className="flex-1" onClick={onCancel}>Cancel</Button>
          <Button type="submit" className="flex-1" loading={busy}>{confirmLabel}</Button>
        </div>
      </form>
    </Modal>
  )
}
