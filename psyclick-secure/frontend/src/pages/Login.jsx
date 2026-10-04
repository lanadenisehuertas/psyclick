import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import { Lock, Activity, ClipboardCheck, ShieldCheck, Copy, Check, ArrowRight, KeyRound, UserPlus } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import { Alert, Button, Field, PasswordInput, Spinner, inputCls, EASE } from '../components/ui.jsx'
import { HOME_FOR_ROLE } from '../lib/roles.js'

const BENEFITS = [
  { icon: Activity,       title: 'Behaviour you can see', text: 'Typing rhythm and mouse movement, measured during a guided session.' },
  { icon: ClipboardCheck, title: 'Validated questionnaires', text: 'PHQ-9 and GAD-7 scored and shown in one clear report.' },
  { icon: ShieldCheck,    title: 'Private by design', text: 'Data stays on this computer, encrypted, with a full audit trail.' },
]

function passwordChecks(pwd) {
  return [
    { ok: pwd.length >= 12, label: 'At least 12 characters' },
    { ok: /[A-Za-z]/.test(pwd), label: 'Contains a letter' },
    { ok: /\d/.test(pwd), label: 'Contains a number' },
  ]
}

function BrandPanel() {
  return (
    <div className="hidden lg:flex w-[46%] max-w-[640px] relative overflow-hidden flex-col justify-between p-12 text-white"
      style={{ background: 'linear-gradient(150deg, #0D2D2D 0%, #0B4A49 55%, #0A7A78 100%)' }}>
      {/* Calm "signal" lines: a nod to keystroke rhythm */}
      <svg className="absolute inset-x-0 bottom-0 w-full h-64 opacity-30" viewBox="0 0 600 200" preserveAspectRatio="none" aria-hidden="true">
        {[0, 1, 2].map(i => (
          <motion.path key={i}
            d={`M0 ${120 + i * 22} C 80 ${60 + i * 20}, 140 ${170 - i * 10}, 220 ${110 + i * 15} S 380 ${50 + i * 25}, 450 ${120 + i * 12} S 560 ${150 - i * 18}, 600 ${100 + i * 20}`}
            fill="none" stroke={i === 1 ? '#7FE3E0' : '#0ABFBC'} strokeWidth={i === 1 ? 2.5 : 1.5}
            initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 2.2, delay: 0.2 * i, ease: EASE }} />
        ))}
      </svg>
      <div className="relative">
        <img src={`${import.meta.env.BASE_URL}images/LOGO%20WITH%20WORD%20white.png`} alt="PsyClick"
          className="h-12 object-contain"
          onError={(e) => { e.currentTarget.src = `${import.meta.env.BASE_URL}images/LOGOggg.png` }} />
        <h1 className="mt-14 text-[40px] leading-[1.1] font-bold tracking-tight max-w-[14ch]">
          A clearer picture, in one short session.
        </h1>
        <p className="mt-4 text-lg text-white/75 max-w-[42ch]">
          Clinical decision support that pairs questionnaires with how a person types and moves.
        </p>
      </div>
      <ul className="relative space-y-5 mt-10">
        {BENEFITS.map((b, i) => (
          <motion.li key={b.title} className="flex gap-4"
            initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, delay: 0.15 + i * 0.08, ease: EASE }}>
            <span className="w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center flex-shrink-0"><b.icon size={20} aria-hidden="true" /></span>
            <div>
              <p className="font-semibold">{b.title}</p>
              <p className="text-white/70 text-[15px]">{b.text}</p>
            </div>
          </motion.li>
        ))}
      </ul>
    </div>
  )
}

export default function Login() {
  const navigate  = useNavigate()
  const location  = useLocation()
  const { setUser } = useApp()

  const [mode, setMode]     = useState('loading')   // loading | offline | setup | signin | created
  const [id, setId]         = useState('')
  const [name, setName]     = useState('')
  const [pwd, setPwd]       = useState('')
  const [pwd2, setPwd2]     = useState('')
  const [err, setErr]       = useState('')
  const [fieldErr, setFieldErr] = useState({})
  const [busy, setBusy]     = useState(false)
  const [created, setCreated] = useState(null)
  const [copied, setCopied] = useState(false)
  const expired = location.state?.reason === 'expired'

  async function checkSetup() {
    setMode('loading')
    const res = await api.setupStatus()
    if (res?.has_accounts === undefined) { setErr(res?.error || ''); setMode('offline'); return }
    setErr('')
    setMode(res.has_accounts ? 'signin' : 'setup')
  }
  useEffect(() => { checkSetup() }, [])

  async function handleLogin(e) {
    e.preventDefault()
    const fe = {}
    if (!id.trim()) fe.id = 'Enter your Clinician ID.'
    else if (!/^\d+$/.test(id.trim())) fe.id = 'Your Clinician ID is a number, for example 2026001.'
    if (!pwd) fe.pwd = 'Enter your password.'
    setFieldErr(fe); setErr('')
    if (Object.keys(fe).length) return
    setBusy(true)
    const res = await api.login(id.trim(), pwd)
    setBusy(false)
    if (res.success) {
      api.setSession(res)
      const role = res.role || 'clinician'
      setUser({ name: res.name, id: res.id, role })
      navigate(HOME_FOR_ROLE[role] || '/dashboard', { replace: true })
    } else {
      setErr(res.error || 'Sign-in failed. Check your ID and password.')
      setPwd('')
    }
  }

  async function handleSetup(e) {
    e.preventDefault()
    const fe = {}
    if (!name.trim()) fe.name = 'Enter your full name.'
    if (!passwordChecks(pwd).every(c => c.ok)) fe.pwd = 'Choose a password that meets all three rules.'
    else if (pwd !== pwd2) fe.pwd2 = 'The two passwords do not match.'
    setFieldErr(fe); setErr('')
    if (Object.keys(fe).length) return
    setBusy(true)
    const res = await api.register(name.trim(), pwd)
    setBusy(false)
    if (res.success) {
      setCreated({ id: res.clinician_id, name: res.name })
      setId(String(res.clinician_id)); setPwd(''); setPwd2('')
      setMode('created')
    } else setErr(res.error || 'Could not create the account.')
  }

  async function copyId() {
    try { await navigator.clipboard.writeText(String(created.id)); setCopied(true); setTimeout(() => setCopied(false), 2000) } catch (_) {}
  }

  const checks = passwordChecks(pwd)

  return (
    <div className="h-screen flex overflow-hidden bg-bg">
      <BrandPanel />
      <main className="flex-1 overflow-y-auto app-canvas flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-[440px]">
          <AnimatePresence mode="wait">
            <motion.div key={mode} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25, ease: EASE }}>

              {mode === 'loading' && <Spinner label="Connecting to PsyClick…" />}

              {mode === 'offline' && (
                <div>
                  <h2 className="text-3xl font-bold text-tmain">Can't reach PsyClick</h2>
                  <p className="text-tsub mt-2">The local PsyClick service isn't responding. It usually starts with the app.</p>
                  <Alert tone="error" className="mt-6" title="What to try">
                    Wait a few seconds and retry. If it keeps failing, close PsyClick completely and open it again.
                  </Alert>
                  <Button className="w-full mt-6" size="lg" onClick={checkSetup}>Try again</Button>
                </div>
              )}

              {mode === 'signin' && (
                <form onSubmit={handleLogin} noValidate>
                  <h2 className="text-3xl font-bold text-tmain">Welcome back</h2>
                  <p className="text-tsub mt-1.5">Sign in with your Clinician ID and password.</p>
                  {expired && !err && (
                    <Alert tone="info" className="mt-6" title="You were signed out">
                      For privacy, PsyClick signs you out after 15 minutes without activity.
                    </Alert>
                  )}
                  {err && <Alert tone="error" className="mt-6">{err}</Alert>}
                  <div className="mt-6 space-y-5">
                    <Field label="Clinician ID" error={fieldErr.id} hint="The number you were given, e.g. 2026001">
                      {(p) => <input {...p} className={inputCls} inputMode="numeric" autoComplete="username" autoFocus
                        value={id} onChange={e => { setId(e.target.value); setFieldErr(f => ({ ...f, id: undefined })) }} />}
                    </Field>
                    <Field label="Password" error={fieldErr.pwd}>
                      {(p) => <PasswordInput {...p} autoComplete="current-password" value={pwd}
                        onChange={e => { setPwd(e.target.value); setFieldErr(f => ({ ...f, pwd: undefined })) }} />}
                    </Field>
                  </div>
                  <Button type="submit" size="lg" className="w-full mt-7" loading={busy} iconRight={busy ? undefined : ArrowRight}>
                    {busy ? 'Signing in…' : 'Sign in'}
                  </Button>
                  <div className="mt-6 rounded-xl bg-white border border-border p-4 text-sm text-tsub space-y-2">
                    <p className="flex gap-2"><KeyRound size={16} className="text-accent-ink flex-shrink-0 mt-0.5" aria-hidden="true" />
                      Forgot your password or locked out? Your administrator can reset access in the Security center.</p>
                    <p className="flex gap-2"><UserPlus size={16} className="text-accent-ink flex-shrink-0 mt-0.5" aria-hidden="true" />
                      New here? Ask your administrator to create your account.</p>
                  </div>
                  <p className="mt-6 text-xs text-tsub flex items-center gap-1.5 justify-center">
                    <Lock size={13} aria-hidden="true" /> Data is encrypted and stored only on this computer.
                  </p>
                </form>
              )}

              {mode === 'setup' && (
                <form onSubmit={handleSetup} noValidate>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent-ink">First-time setup</p>
                  <h2 className="text-3xl font-bold text-tmain mt-1.5">Create the administrator</h2>
                  <p className="text-tsub mt-1.5">This first account manages PsyClick and creates accounts for other clinicians.</p>
                  {err && <Alert tone="error" className="mt-6">{err}</Alert>}
                  <div className="mt-6 space-y-5">
                    <Field label="Full name" error={fieldErr.name} required>
                      {(p) => <input {...p} className={inputCls} autoComplete="name" autoFocus placeholder="e.g. Dr. Maria Santos"
                        value={name} onChange={e => { setName(e.target.value); setFieldErr(f => ({ ...f, name: undefined })) }} />}
                    </Field>
                    <Field label="Password" error={fieldErr.pwd} required>
                      {(p) => <PasswordInput {...p} autoComplete="new-password" value={pwd}
                        onChange={e => { setPwd(e.target.value); setFieldErr(f => ({ ...f, pwd: undefined })) }} />}
                    </Field>
                    <ul className="grid grid-cols-1 gap-1.5 -mt-2" aria-label="Password rules">
                      {checks.map(c => (
                        <li key={c.label} className={`text-sm flex items-center gap-2 ${c.ok ? 'text-success-ink' : 'text-tsub'}`}>
                          <span className={`w-4 h-4 rounded-full flex items-center justify-center ${c.ok ? 'bg-success text-white' : 'border border-[#B7CCCC]'}`} aria-hidden="true">
                            {c.ok && <Check size={11} strokeWidth={3} />}
                          </span>
                          {c.label}<span className="sr-only">{c.ok ? ' — done' : ' — not yet'}</span>
                        </li>
                      ))}
                    </ul>
                    <Field label="Repeat password" error={fieldErr.pwd2} required>
                      {(p) => <PasswordInput {...p} autoComplete="new-password" value={pwd2}
                        onChange={e => { setPwd2(e.target.value); setFieldErr(f => ({ ...f, pwd2: undefined })) }} />}
                    </Field>
                  </div>
                  <Button type="submit" size="lg" className="w-full mt-7" loading={busy}>Create administrator</Button>
                </form>
              )}

              {mode === 'created' && created && (
                <div className="text-center">
                  <motion.span className="mx-auto w-16 h-16 rounded-full bg-success text-white flex items-center justify-center"
                    initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: 'spring', stiffness: 260, damping: 18 }}>
                    <Check size={32} strokeWidth={3} aria-hidden="true" />
                  </motion.span>
                  <h2 className="text-3xl font-bold text-tmain mt-5">You're all set, {created.name.split(' ')[0]}</h2>
                  <p className="text-tsub mt-2">You will sign in with this Clinician ID. Write it down somewhere safe.</p>
                  <div className="mt-6 rounded-2xl bg-white border-2 border-dashed border-accent/50 p-6">
                    <p className="text-sm font-semibold text-tsub uppercase tracking-wider">Your Clinician ID</p>
                    <p className="text-5xl font-bold text-tmain tracking-wider mt-2 tabular-nums">{created.id}</p>
                    <Button variant="secondary" size="sm" className="mt-4" icon={copied ? Check : Copy} onClick={copyId}>
                      {copied ? 'Copied' : 'Copy ID'}
                    </Button>
                  </div>
                  <Button size="lg" className="w-full mt-7" iconRight={ArrowRight} onClick={() => { setErr(''); setMode('signin') }}>
                    Continue to sign in
                  </Button>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  )
}
