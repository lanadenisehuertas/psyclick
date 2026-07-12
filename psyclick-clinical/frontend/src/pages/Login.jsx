import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lock } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'

export default function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const [id,   setId]   = useState('')
  const [name, setName] = useState('')
  const [pwd,  setPwd]  = useState('')
  const [err,  setErr]  = useState('')
  const [busy, setBusy] = useState(false)
  const { setUser }     = useApp()
  const navigate        = useNavigate()
  const pwdRef          = useRef(null)

  async function handleLogin() {
    setErr('')
    if (!id || !pwd) { setErr('Please enter your Clinician ID and Password.'); return }
    setBusy(true)
    try {
      const res = await api.login(id, pwd)
      if (res.success) {
        api.setSession(res)
        setUser({ name: res.name, id: res.id, role: res.role || 'clinician' })
        navigate('/dashboard')
      }
      else setErr(res.error || 'Sign in failed. Please check the ID, password, and database connection.')
    } catch (e) {
      setErr(e?.message || 'Sign in failed unexpectedly.')
    } finally {
      setBusy(false)
    }
  }

  async function handleRegister() {
    setErr('')
    if (!name || !pwd) { setErr('Please enter your name and password.'); return }
    if (pwd.length < 12 || !/[A-Za-z]/.test(pwd) || !/\d/.test(pwd)) {
      setErr('Password must be at least 12 characters and contain a letter and number.')
      return
    }
    setBusy(true)
    try {
      const res = await api.register(name, pwd)
      if (res.success) {
        setErr(`Registration successful! Your Clinician ID is: ${res.clinician_id}`)
        setIsRegister(false)
        setName('')
        setId(String(res.clinician_id))
        setPwd('')
      } else setErr(res.error || 'Registration failed. Please check the database connection.')
    } catch (e) {
      setErr(e?.message || 'Registration failed unexpectedly.')
    } finally {
      setBusy(false)
    }
  }

  const features = [
    'Biometric psychomotor analysis',
    'Validated PHQ-9 & GAD-7 screening',
    'Local-first storage with encrypted exports and backups',
  ]

  return (
    <div className="h-screen flex overflow-hidden animate-fade-in">
      {/* ── Left teal panel ── */}
      <div className="w-[420px] flex-shrink-0 bg-accent flex flex-col items-center justify-center px-10 relative overflow-hidden animate-slide-right">
        {/* Decorative floating orbs */}
        <div className="absolute top-[-60px] right-[-60px] w-48 h-48 rounded-full bg-white/10 animate-float" style={{ animationDelay: '2s' }} />
        <div className="absolute bottom-[80px] left-[-40px] w-32 h-32 rounded-full bg-white/[0.08] animate-float" style={{ animationDelay: '4s' }} />
        <div className="absolute top-[40%] right-[-20px] w-20 h-20 rounded-full bg-adark/40 animate-float" style={{ animationDelay: '1s' }} />

        <div className="text-center relative z-10">
          <img
            src={`${import.meta.env.BASE_URL}images/LOGO%20WITH%20WORD%20white.png`}
            alt="PsyClick"
            className="h-16 object-contain mx-auto mb-8 animate-fade-up-1"
            onError={(e) => { e.currentTarget.src = `${import.meta.env.BASE_URL}images/LOGOggg.png` }}
          />
          <p className="text-white/80 text-base animate-fade-up-2">Clinical Decision Support System</p>
          <div className="mt-10 space-y-3 text-left animate-fade-up-3">
            {features.map((f, i) => (
              <div
                key={f}
                className="flex items-center gap-3 text-white/75 text-sm transition-all duration-300 hover:text-white hover:translate-x-1"
                style={{ transitionDelay: `${i * 40}ms` }}
              >
                <div className="w-5 h-5 rounded-full bg-white/25 flex items-center justify-center flex-shrink-0 animate-shimmer">
                  <span className="text-xs">✓</span>
                </div>
                {f}
              </div>
            ))}
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-adark" />
      </div>

      {/* ── Right form panel ── */}
      <div className="flex-1 bg-bg flex items-center justify-center px-16">
        <div className="w-full max-w-[400px] animate-slide-up">
          <h2 className="text-3xl font-bold text-tmain mb-1">
            {isRegister ? 'Create Account' : 'Welcome back'}
          </h2>
          <p className="text-tsub text-base mb-8">
            {isRegister ? 'Register as a new clinician' : 'Sign in to your clinician account'}
          </p>

          <div className="bg-white rounded-card shadow-card p-8 border border-border transition-shadow duration-300 hover:shadow-hover">
            {isRegister ? (
              <form onSubmit={e => { e.preventDefault(); handleRegister() }}>
                <div className="mb-5">
                  <label className="text-sm font-semibold text-tmain mb-2 block" htmlFor="reg-name">Full Name</label>
                  <input
                    id="reg-name"
                    className="input-field"
                    placeholder="Dr. Example"
                    autoComplete="name"
                    value={name}
                    onChange={e => { setName(e.target.value); setErr('') }}
                    onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), pwdRef.current?.focus())}
                  />
                </div>
                <div className="mb-4">
                  <label className="text-sm font-semibold text-tmain mb-2 block" htmlFor="reg-pwd">
                    Password <span className="text-tsub font-normal">(min. 8 characters)</span>
                  </label>
                  <input
                    id="reg-pwd"
                    ref={pwdRef}
                    className="input-field"
                    type="password"
                    placeholder="Create a secure password"
                    autoComplete="new-password"
                    value={pwd}
                    onChange={e => { setPwd(e.target.value); setErr('') }}
                  />
                </div>

                {err && (
                  <p className={`text-sm mb-4 animate-fade-up-1 ${err.includes('successful') ? 'text-success' : 'text-coral'}`}>
                    {err}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={busy}
                  className="btn-primary w-full text-base mb-5 transition-transform duration-150 hover:scale-[1.02] active:scale-[0.97]"
                >
                  {busy ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                      Registering…
                    </span>
                  ) : 'Register →'}
                </button>

                <button
                  type="button"
                  onClick={() => { setIsRegister(false); setErr(''); setName(''); setPwd(''); }}
                  className="w-full text-center text-tsub text-sm hover:text-accent transition-colors"
                >
                  Already have an account? Sign in
                </button>
              </form>
            ) : (
              <form onSubmit={e => { e.preventDefault(); handleLogin() }}>
                <div className="mb-5">
                  <label className="text-sm font-semibold text-tmain mb-2 block" htmlFor="login-id">Clinician ID</label>
                  <input
                    id="login-id"
                    className="input-field"
                    placeholder="Enter your clinician ID"
                    autoComplete="username"
                    value={id}
                    onChange={e => { setId(e.target.value); setErr('') }}
                  />
                </div>
                <div className="mb-4">
                  <label className="text-sm font-semibold text-tmain mb-2 block" htmlFor="login-pwd">Password</label>
                  <input
                    id="login-pwd"
                    className="input-field"
                    type="password"
                    placeholder="Enter your password"
                    autoComplete="current-password"
                    value={pwd}
                    onChange={e => { setPwd(e.target.value); setErr('') }}
                  />
                </div>

                {err && (
                  <p className="text-coral text-sm mb-4 animate-fade-up-1">{err}</p>
                )}

                <button
                  type="submit"
                  disabled={busy}
                  className="btn-primary w-full text-base mb-5 transition-transform duration-150 hover:scale-[1.02] active:scale-[0.97]"
                >
                  {busy ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                      Signing in…
                    </span>
                  ) : 'Sign In →'}
                </button>

                <div className="flex items-center gap-2 bg-accent/10 rounded-xl px-4 py-3 mb-4 transition-colors duration-200 hover:bg-accent/15">
                  <Lock size={14} className="text-accent flex-shrink-0" />
                  <span className="text-accent text-xs">All data encrypted and stored locally</span>
                </div>

                <button
                  type="button"
                  onClick={() => { setIsRegister(true); setErr(''); setId(''); setPwd(''); }}
                  className="w-full text-center text-tsub text-sm hover:text-accent transition-colors"
                >
                  Don't have an account? Register
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
