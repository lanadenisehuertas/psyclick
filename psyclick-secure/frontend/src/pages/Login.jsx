import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence, useReducedMotion } from 'motion/react'
import { Lock, Activity, ClipboardCheck, ShieldCheck, Copy, Check, ArrowRight, KeyRound, UserPlus } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import { Alert, Button, Field, PasswordInput, Spinner, inputCls, EASE } from '../components/ui.jsx'
import { HOME_FOR_ROLE } from '../lib/roles.js'
import AnimatedLogo from '../components/AnimatedLogo.jsx'

function passwordChecks(pwd) {
  return [
    { ok: pwd.length >= 12, label: 'At least 12 characters' },
    { ok: /[A-Za-z]/.test(pwd), label: 'Contains a letter' },
    { ok: /\d/.test(pwd), label: 'Contains a number' },
  ]
}

const BENEFITS = [
  { icon: Activity,       title: 'Behaviour you can see', text: 'Typing rhythm and mouse movement, measured during a guided session.', tint: 'rgba(112,232,192,.16)', ink: '#70E8C0' },
  { icon: ClipboardCheck, title: 'Validated questionnaires', text: 'PHQ-9 and GAD-7 scored and shown in one clear report.', tint: 'rgba(104,216,232,.16)', ink: '#68D8E8' },
  { icon: ShieldCheck,    title: 'Private by design', text: 'Data stays on this computer, encrypted, with a full audit trail.', tint: 'rgba(120,168,216,.2)', ink: '#9DC0E8' },
]

// Small floating cards around the logo: what PsyClick measures
function FloatChip({ className, delay, children }) {
  const still = useReducedMotion()
  return (
    <motion.div className={`absolute rounded-2xl border border-white/15 bg-white/[0.08] backdrop-blur-md px-3.5 py-2.5 shadow-[0_12px_30px_-12px_rgba(0,0,0,.5)] ${className}`}
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: still ? 0 : [0, -5, 0] }}
      transition={{ opacity: { delay, duration: 0.5 }, y: still ? { delay, duration: 0.5 } : { delay, duration: 5, repeat: Infinity, ease: 'easeInOut' } }}>
      {children}
    </motion.div>
  )
}

function RhythmBars() {
  const still = useReducedMotion()
  const H = [10, 18, 7, 22, 13, 16, 9, 20]
  return (
    <span className="flex items-end gap-[3px] h-6">
      {H.map((h, i) => (
        <motion.span key={i} className="w-[4px] rounded-full" style={{ height: h, background: i % 3 === 0 ? '#70E8C0' : i % 3 === 1 ? '#68D8E8' : '#78A8D8', originY: 1 }}
          animate={still ? undefined : { scaleY: [1, 0.45, 1.1, 0.8, 1] }}
          transition={{ duration: 1.8, delay: i * 0.12, repeat: Infinity, ease: 'easeInOut' }} />
      ))}
    </span>
  )
}

function BrandPanel() {
  const still = useReducedMotion()
  return (
    <div className="hidden lg:flex w-[46%] max-w-[640px] relative overflow-hidden flex-col p-12 text-white"
      style={{ background: 'radial-gradient(40rem 26rem at 0% 100%, rgba(112,232,192,0.22), transparent 70%), radial-gradient(36rem 26rem at 100% 0%, rgba(120,168,216,0.28), transparent 70%), linear-gradient(160deg, #0F2A33 0%, #0D3440 55%, #12304A 100%)' }}>
      {/* Drifting colour fields */}
      {[
        { c: 'rgba(112,232,192,.30)', s: 340, x: '-10%', y: '58%', d: 18 },
        { c: 'rgba(104,216,232,.24)', s: 280, x: '62%', y: '8%', d: 22 },
        { c: 'rgba(120,168,216,.30)', s: 300, x: '55%', y: '66%', d: 26 },
      ].map((b, i) => (
        <motion.div key={i} className="absolute rounded-full blur-3xl pointer-events-none" aria-hidden="true"
          style={{ width: b.s, height: b.s, left: b.x, top: b.y, background: b.c }}
          animate={still ? undefined : { x: [0, 30, -20, 0], y: [0, -24, 16, 0] }}
          transition={{ duration: b.d, repeat: Infinity, ease: 'easeInOut' }} />
      ))}
      {/* Dot grid */}
      <div className="absolute inset-0 opacity-[0.18] pointer-events-none" aria-hidden="true"
        style={{ backgroundImage: 'radial-gradient(rgba(255,255,255,.55) 1px, transparent 1px)', backgroundSize: '22px 22px', maskImage: 'radial-gradient(ellipse at 50% 38%, black 20%, transparent 70%)', WebkitMaskImage: 'radial-gradient(ellipse at 50% 38%, black 20%, transparent 70%)' }} />
      {/* Keystroke-rhythm lines */}
      <svg className="absolute inset-x-0 top-[60%] w-full h-44 opacity-40 pointer-events-none" viewBox="0 0 600 200" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="lg-wave" x1="0" x2="1">
            <stop offset="0" stopColor="#70E8C0" /><stop offset=".5" stopColor="#68D8E8" /><stop offset="1" stopColor="#78A8D8" />
          </linearGradient>
        </defs>
        {[0, 1, 2].map(i => (
          <motion.path key={i}
            d={`M0 ${120 + i * 22} C 80 ${60 + i * 20}, 140 ${170 - i * 10}, 220 ${110 + i * 15} S 380 ${50 + i * 25}, 450 ${120 + i * 12} S 560 ${150 - i * 18}, 600 ${100 + i * 20}`}
            fill="none" stroke="url(#lg-wave)" strokeWidth={i === 1 ? 2.2 : 1.2} strokeOpacity={i === 1 ? 1 : 0.6}
            initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 2.2, delay: 0.2 * i, ease: EASE }} />
        ))}
      </svg>

      <div className="relative flex-1 flex flex-col items-center justify-center text-center">
        <div className="relative">
          <AnimatedLogo size={196} />
          <FloatChip className="-left-[150px] top-6 text-left" delay={0.8}>
            <p className="text-[11px] uppercase tracking-wider text-white/60 font-semibold">Typing rhythm</p>
            <div className="mt-1"><RhythmBars /></div>
          </FloatChip>
          <FloatChip className="-right-[178px] top-[56%] text-left" delay={1.1}>
            <p className="text-[11px] uppercase tracking-wider text-white/60 font-semibold">Questionnaires</p>
            <p className="mt-1 flex items-center gap-1.5 text-sm font-semibold"><span className="w-2 h-2 rounded-full bg-mint" />PHQ-9<span className="w-2 h-2 rounded-full bg-peri ml-1.5" />GAD-7</p>
          </FloatChip>
        </div>
        <motion.img src={`${import.meta.env.BASE_URL}images/WORD_.png`} alt="PsyClick" className="h-12 mt-12 object-contain"
          initial={{ opacity: 0, clipPath: 'inset(0 100% 0 0)' }} animate={{ opacity: 1, clipPath: 'inset(0 0% 0 0)' }}
          transition={{ duration: 0.9, delay: 0.35, ease: EASE }} />
        <motion.h1 className="mt-6 font-display text-[34px] leading-[1.1] font-semibold max-w-[20ch]"
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.6, ease: EASE }}>
          A clearer picture, in one short session.
        </motion.h1>
        <motion.p className="mt-3 text-[17px] text-white/75 max-w-[44ch]"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.75 }}>
          Clinical decision support that pairs questionnaires with how a person types and moves.
        </motion.p>
      </div>

      <ul className="relative grid grid-cols-3 gap-3 mt-8">
        {BENEFITS.map((b, i) => (
          <motion.li key={b.title} className="rounded-2xl border border-white/10 p-4 backdrop-blur-sm"
            style={{ background: `linear-gradient(160deg, ${b.tint}, rgba(255,255,255,.03))` }}
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay: 0.9 + i * 0.1, ease: EASE }}>
            <span className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: b.tint, color: b.ink }}>
              <b.icon size={18} aria-hidden="true" />
            </span>
            <p className="font-semibold mt-3 text-[15px] leading-snug">{b.title}</p>
            <p className="text-white/65 text-[13px] mt-1 leading-snug">{b.text}</p>
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
                  <h2 className="font-display text-[32px] font-semibold text-tmain">Can't reach PsyClick</h2>
                  <p className="text-tsub mt-2">The local PsyClick service isn't responding. It usually starts with the app.</p>
                  <Alert tone="error" className="mt-6" title="What to try">
                    Wait a few seconds and retry. If it keeps failing, close PsyClick completely and open it again.
                  </Alert>
                  <Button className="w-full mt-6" size="lg" onClick={checkSetup}>Try again</Button>
                </div>
              )}

              {mode === 'signin' && (
                <form onSubmit={handleLogin} noValidate>
                  <h2 className="font-display text-[32px] font-semibold text-tmain">Welcome back</h2>
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
                  <p className="font-mono text-[13px] text-tsub">First-time setup</p>
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
