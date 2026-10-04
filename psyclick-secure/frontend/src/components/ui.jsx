// PsyClick UI kit — one set of building blocks so every screen behaves the same.
import { createContext, useCallback, useContext, useEffect, useId, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { AlertTriangle, CheckCircle2, Info, XCircle, X, Loader2, Eye, EyeOff } from 'lucide-react'
import Sidebar from './Sidebar.jsx'

export const EASE = [0.22, 1, 0.36, 1]

// ── Page shell (clinician area) ──────────────────────────────────────────────
export function PageShell({ title, subtitle, actions, eyebrow, back, children, width = 'max-w-[1240px]' }) {
  return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main id="main" className="flex-1 overflow-y-auto app-canvas" tabIndex={-1}>
        <div className={`${width} mx-auto px-8 py-7`}>
          {back}
          <header className="flex flex-wrap items-end justify-between gap-4 mb-7">
            <div className="min-w-0">
              {eyebrow && <p className="font-mono text-[13px] text-tsub mb-1">{eyebrow}</p>}
              <h1 className="font-display text-[30px] leading-tight font-semibold text-tmain">{title}</h1>
              {subtitle && <p className="text-tsub mt-1 max-w-[70ch]">{subtitle}</p>}
            </div>
            {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
          </header>
          {children}
        </div>
      </main>
    </div>
  )
}

// ── Buttons ──────────────────────────────────────────────────────────────────
const BTN = {
  primary:   'bg-accent-ink text-white hover:bg-[#08566A] shadow-[0_1px_2px_rgba(15,42,51,0.25),0_6px_14px_-6px_rgba(10,107,128,0.55),inset_0_1px_0_rgba(255,255,255,0.18)]',
  secondary: 'bg-white text-tmain border border-border shadow-[0_1px_2px_rgba(15,42,51,0.06)] hover:border-accent-ink/40 hover:bg-[#F4FAFB]',
  ghost:     'bg-transparent text-tsub hover:bg-black/[0.04] hover:text-tmain',
  danger:    'bg-white text-coral-ink border border-coral/40 hover:bg-coral/10',
  dangerSolid: 'bg-coral-ink text-white hover:bg-[#9E302E]',
}
const SIZE = { sm: 'h-9 px-3.5 text-sm', md: 'h-11 px-5 text-[15px]', lg: 'h-14 px-7 text-lg' }

export function Button({ variant = 'primary', size = 'md', loading = false, icon: Icon, iconRight: IconRight,
  className = '', children, disabled, ...rest }) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex items-center justify-center gap-2 rounded-xl font-semibold whitespace-nowrap select-none cursor-pointer
        transition-[background-color,border-color,color,box-shadow,transform] duration-150 active:scale-[0.98]
        focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-ink
        disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100
        ${BTN[variant]} ${SIZE[size]} ${className}`}
    >
      {loading ? <Loader2 size={size === 'lg' ? 20 : 16} className="animate-spin" aria-hidden="true" />
        : Icon && <Icon size={size === 'lg' ? 20 : 17} aria-hidden="true" />}
      {children}
      {IconRight && !loading && <IconRight size={size === 'lg' ? 20 : 17} aria-hidden="true" />}
    </button>
  )
}

// ── Cards ────────────────────────────────────────────────────────────────────
export function Card({ className = '', children, ...rest }) {
  return <div {...rest} className={`surface ${className}`}>{children}</div>
}

// A whole card that is one action: a real button, with hover lift and focus ring.
export function ActionCard({ onClick, className = '', children, ariaLabel, disabled, style }) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      disabled={disabled}
      style={style}
      whileHover={disabled ? undefined : { y: -3 }}
      whileTap={disabled ? undefined : { scale: 0.985 }}
      transition={{ duration: 0.18, ease: EASE }}
      className={`text-left rounded-[20px] border border-border bg-white shadow-card hover:shadow-hover hover:border-accent-ink/30
        transition-[box-shadow,border-color] duration-200 cursor-pointer disabled:cursor-not-allowed disabled:opacity-60
        focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-ink ${className}`}
    >
      {children}
    </motion.button>
  )
}

export function IconTile({ icon: Icon, tone = 'teal', size = 'md' }) {
  // Outlined, quiet marks; colour only where it carries meaning (amber/coral)
  const tones = {
    teal: 'text-accent-ink', blue: 'text-[#2F6690]', green: 'text-success-ink',
    amber: 'text-amber-ink', coral: 'text-coral-ink', slate: 'text-tmain',
  }
  const s = (size === 'lg' ? 'w-12 h-12' : size === 'sm' ? 'w-8 h-8' : 'w-10 h-10') + ' rounded-full border border-border bg-white'
  return (
    <span className={`inline-flex items-center justify-center flex-shrink-0 ${s} ${tones[tone]}`} aria-hidden="true">
      <Icon size={size === 'lg' ? 24 : size === 'sm' ? 16 : 20} />
    </span>
  )
}

// ── Alerts ───────────────────────────────────────────────────────────────────
const ALERT = {
  info:    { icon: Info,          cls: 'bg-[#EEF6FB] border-[#5BA4CF]/40 text-[#1F4E6E]' },
  success: { icon: CheckCircle2,  cls: 'bg-success/10 border-success/40 text-success-ink' },
  warning: { icon: AlertTriangle, cls: 'bg-amber/12 border-amber/50 text-amber-ink' },
  error:   { icon: XCircle,       cls: 'bg-coral/10 border-coral/40 text-coral-ink' },
}
export function Alert({ tone = 'info', title, children, action, onClose, className = '' }) {
  const a = ALERT[tone]
  const Icon = a.icon
  return (
    <div role={tone === 'error' || tone === 'warning' ? 'alert' : 'status'}
      className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${a.cls} ${className}`}>
      <Icon size={20} className="flex-shrink-0 mt-0.5" aria-hidden="true" />
      <div className="flex-1 min-w-0 text-[15px] leading-relaxed">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={title ? 'mt-0.5 opacity-95' : ''}>{children}</div>}
        {action && <div className="mt-2">{action}</div>}
      </div>
      {onClose && (
        <button onClick={onClose} aria-label="Dismiss" className="p-1 -m-1 rounded-lg hover:bg-black/5 cursor-pointer">
          <X size={16} aria-hidden="true" />
        </button>
      )}
    </div>
  )
}

// ── Form fields ──────────────────────────────────────────────────────────────
export function Field({ label, hint, error, children, required, id: idProp }) {
  const autoId = useId()
  const id = idProp || autoId
  const describedBy = [hint && `${id}-hint`, error && `${id}-err`].filter(Boolean).join(' ') || undefined
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-semibold text-tmain mb-1.5">
        {label}{required && <span className="text-coral-ink ml-0.5" aria-hidden="true">*</span>}
      </label>
      {children({ id, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined })}
      {hint && !error && <p id={`${id}-hint`} className="text-sm text-tsub mt-1.5">{hint}</p>}
      {error && <p id={`${id}-err`} className="text-sm text-coral-ink mt-1.5 flex items-center gap-1.5"><XCircle size={14} aria-hidden="true" />{error}</p>}
    </div>
  )
}

export const inputCls = `w-full h-12 px-4 rounded-xl border border-border bg-white text-tmain text-base
  placeholder:text-[#8AA3A3] outline-none transition-[border-color,box-shadow] duration-150
  focus:border-accent-ink focus:ring-4 focus:ring-accent/15 aria-[invalid=true]:border-coral-ink aria-[invalid=true]:ring-coral/15`

export function PasswordInput({ value, onChange, capsHint = true, ...rest }) {
  const [show, setShow] = useState(false)
  const [caps, setCaps] = useState(false)
  return (
    <div>
      <div className="relative">
        <input
          {...rest}
          type={show ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          onKeyUp={e => setCaps(e.getModifierState?.('CapsLock'))}
          className={`${inputCls} pr-12`}
        />
        <button type="button" onClick={() => setShow(s => !s)}
          aria-label={show ? 'Hide password' : 'Show password'}
          className="absolute right-2 top-1/2 -translate-y-1/2 w-9 h-9 rounded-lg flex items-center justify-center text-tsub hover:text-tmain hover:bg-black/[0.04] cursor-pointer">
          {show ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
        </button>
      </div>
      {capsHint && caps && <p className="text-sm text-amber-ink mt-1.5">Caps Lock is on.</p>}
    </div>
  )
}

// ── Modal / confirm dialog ───────────────────────────────────────────────────
export function Modal({ open, onClose, title, description, children, width = 'max-w-md', dismissible = true }) {
  const ref = useRef(null)
  const titleId = useId()
  useEffect(() => {
    if (!open) return
    const prev = document.activeElement
    const t = setTimeout(() => ref.current?.querySelector('[data-autofocus], input, button')?.focus(), 30)
    function onKey(e) {
      if (e.key === 'Escape' && dismissible) onClose?.()
      if (e.key === 'Tab' && ref.current) {
        const f = [...ref.current.querySelectorAll('button, input, select, textarea, a[href]')].filter(el => !el.disabled)
        if (!f.length) return
        if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus() }
        else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus() }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => { clearTimeout(t); window.removeEventListener('keydown', onKey); prev?.focus?.() }
  }, [open, dismissible, onClose])

  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-[100] flex items-center justify-center p-6"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
          <div className="absolute inset-0 bg-[#0D2D2D]/50 backdrop-blur-[2px]" onClick={dismissible ? onClose : undefined} aria-hidden="true" />
          <motion.div
            ref={ref}
            role="dialog" aria-modal="true" aria-labelledby={titleId}
            initial={{ opacity: 0, y: 16, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.22, ease: EASE }}
            className={`relative w-full ${width} bg-white rounded-3xl shadow-modal p-7`}
          >
            {dismissible && (
              <button onClick={onClose} aria-label="Close" className="absolute right-4 top-4 w-9 h-9 rounded-xl flex items-center justify-center text-tsub hover:bg-black/[0.05] hover:text-tmain cursor-pointer">
                <X size={18} aria-hidden="true" />
              </button>
            )}
            <h2 id={titleId} className="text-xl font-bold text-tmain pr-8">{title}</h2>
            {description && <p className="text-tsub mt-1.5 leading-relaxed">{description}</p>}
            <div className="mt-5">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export function ConfirmDialog({ open, title, description, confirmLabel = 'Confirm', cancelLabel = 'Cancel',
  danger = false, busy = false, confirmDisabled = false, onConfirm, onCancel, children }) {
  return (
    <Modal open={open} onClose={onCancel} title={title} description={description}>
      {children}
      <div className="flex gap-3 mt-6">
        <Button variant="secondary" className="flex-1" onClick={onCancel} data-autofocus>{cancelLabel}</Button>
        <Button variant={danger ? 'dangerSolid' : 'primary'} className="flex-1" loading={busy} disabled={confirmDisabled} onClick={onConfirm}>{confirmLabel}</Button>
      </div>
    </Modal>
  )
}

// ── Empty / loading states ───────────────────────────────────────────────────
export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-col items-center text-center px-6 py-14">
      {Icon && <IconTile icon={Icon} tone="teal" size="lg" />}
      <p className="mt-4 font-display text-lg font-semibold text-tmain">{title}</p>
      {children && <p className="mt-1 text-tsub max-w-[48ch]">{children}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-xl bg-[#E6EFEF] ${className}`} aria-hidden="true" />
}

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-tsub" role="status">
      <Loader2 size={28} className="animate-spin text-accent-ink" aria-hidden="true" />
      <p>{label}</p>
    </div>
  )
}

// ── Segmented control (tabs / filters) ───────────────────────────────────────
export function Segmented({ value, onChange, options, ariaLabel }) {
  return (
    <div role="tablist" aria-label={ariaLabel} className="inline-flex p-1 rounded-xl bg-white/80 border border-border shadow-card backdrop-blur">
      {options.map(o => {
        const active = o.value === value
        return (
          <button key={o.value} role="tab" aria-selected={active} onClick={() => onChange(o.value)}
            className={`relative h-9 px-4 rounded-lg text-sm font-semibold cursor-pointer transition-colors
              focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-ink
              ${active ? 'text-white' : 'text-tsub hover:text-tmain'}`}>
            {active && <motion.span layoutId={`seg-${ariaLabel}`} className="absolute inset-0 rounded-lg bg-accent-ink" transition={{ duration: 0.2, ease: EASE }} />}
            <span className="relative inline-flex items-center gap-1.5">
              {o.icon && <o.icon size={15} aria-hidden="true" />}
              {o.label}
              {o.count != null && <span className={`text-xs rounded-full px-1.5 ${active ? 'bg-white/20' : 'bg-bg'}`}>{o.count}</span>}
            </span>
          </button>
        )
      })}
    </div>
  )
}

// ── Toasts (brief success / error feedback) ──────────────────────────────────
const ToastCtx = createContext(() => {})
export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const push = useCallback((message, tone = 'success') => {
    const id = Math.random().toString(36).slice(2)
    setItems(list => [...list, { id, message, tone }])
    setTimeout(() => setItems(list => list.filter(t => t.id !== id)), 4200)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-6 right-6 z-[200] flex flex-col gap-2 w-[360px]" aria-live="polite">
        <AnimatePresence>
          {items.map(t => (
            <motion.div key={t.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.2, ease: EASE }}>
              <Alert tone={t.tone} className="shadow-modal bg-white">{t.message}</Alert>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  )
}
export const useToast = () => useContext(ToastCtx)
