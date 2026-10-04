import { NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Users, ClipboardList, LogOut, Cloud, CloudOff, RefreshCw, ShieldCheck, Plus } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../api/psyclick.js'
import { useState, useEffect, useCallback } from 'react'

const ROLE_LABEL = { admin: 'Administrator', clinician: 'Clinician', auditor: 'Auditor' }

const NAV_SECTIONS = [
  {
    label: 'Clinic',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', roles: ['admin', 'clinician'] },
      { to: '/clients',   icon: Users,           label: 'Clients',   roles: ['admin', 'clinician'] },
    ],
  },
  {
    label: 'Administration',
    items: [
      { to: '/audit',    icon: ClipboardList, label: 'Audit log',       roles: ['admin', 'auditor'] },
      { to: '/security', icon: ShieldCheck,   label: 'Security center', roles: ['admin'] },
    ],
  },
]

// ── Cloud sync status (only when Supabase sync is configured) ────────────────
function SyncBadge() {
  const [sync,    setSync]    = useState(null)
  const [syncing, setSyncing] = useState(false)

  const refresh = useCallback(async () => {
    try { const res = await api.syncStatus(); if (res) setSync(res) } catch (_) { /* backend not ready */ }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 30_000)
    return () => clearInterval(id)
  }, [refresh])

  async function handleSyncNow() {
    setSyncing(true)
    try { const res = await api.syncNow(); if (res) setSync(res) } catch (_) {}
    setSyncing(false)
    setTimeout(refresh, 2000)
  }

  if (!sync || !sync.enabled) return null
  const pending = sync.pending || 0
  const busy = syncing || sync.syncing
  const label = busy ? 'Syncing…'
    : !sync.connected ? (pending ? `${pending} waiting — offline` : 'Offline')
    : pending ? `${pending} record${pending !== 1 ? 's' : ''} waiting`
    : sync.last_sync ? `Synced ${sync.last_sync.slice(11, 16)}` : 'Synced'
  const Icon = (!sync.connected || pending > 0) ? CloudOff : Cloud

  return (
    <div className="px-3 pb-2">
      <button onClick={handleSyncNow} disabled={busy} title={sync.error || 'Sync now'}
        className="flex items-center gap-2 w-full px-3 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-medium text-[#A9CACA] disabled:opacity-60 cursor-pointer">
        {busy ? <RefreshCw size={14} className="animate-spin" aria-hidden="true" /> : <Icon size={14} aria-hidden="true" />}
        <span className="truncate">{label}</span>
      </button>
    </div>
  )
}

export default function Sidebar() {
  const { user, setUser } = useApp()
  const navigate = useNavigate()
  const role = user?.role || 'clinician'
  const canAssess = role === 'admin' || role === 'clinician'

  async function handleLogout() {
    await api.logout()
    setUser(null)
    navigate('/')
  }

  const initials = (user?.name || 'U').split(' ').filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase()

  return (
    <aside className="w-60 flex-shrink-0 h-full flex flex-col bg-sidebar select-none" aria-label="Main navigation">
      <div className="px-5 pt-6 pb-6 flex items-center gap-3">
        <img src={`${import.meta.env.BASE_URL}images/LOGOggg.png`} alt="" className="w-9 h-9 object-contain flex-shrink-0" />
        <div>
          <p className="text-white text-base font-bold leading-tight">PsyClick</p>
          <p className="text-[#9BBFBF] text-xs leading-tight font-medium">Secure Edition</p>
        </div>
      </div>

      {canAssess && (
        <div className="px-3 mb-5">
          <button onClick={() => navigate('/intake')}
            className="w-full h-11 rounded-xl bg-accent text-[#06302F] font-bold text-[15px] flex items-center justify-center gap-2 hover:bg-[#2FD3D0] transition-colors cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">
            <Plus size={18} aria-hidden="true" /> New assessment
          </button>
        </div>
      )}

      <nav className="flex-1 px-3 overflow-y-auto pb-3 space-y-5">
        {NAV_SECTIONS.map(section => {
          const items = section.items.filter(item => item.roles.includes(role))
          if (!items.length) return null
          return (
            <div key={section.label}>
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#6E9696] px-3 mb-1.5">{section.label}</p>
              <div className="space-y-1">
                {items.map(({ to, icon: Icon, label }) => (
                  <NavLink key={to} to={to}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3.5 h-11 rounded-xl text-[15px] font-medium transition-colors cursor-pointer
                       focus-visible:outline focus-visible:outline-2 focus-visible:outline-white
                       ${isActive ? 'bg-white/[0.10] text-white' : 'text-[#A9CACA] hover:bg-white/[0.06] hover:text-white'}`}>
                    {({ isActive }) => (<>
                      <span className={`w-1 h-5 rounded-full -ml-2 mr-0.5 ${isActive ? 'bg-accent' : 'bg-transparent'}`} aria-hidden="true" />
                      <Icon size={18} aria-hidden="true" />
                      {label}
                    </>)}
                  </NavLink>
                ))}
              </div>
            </div>
          )
        })}
      </nav>

      <SyncBadge />

      <div className="mx-3 mb-4 mt-1 rounded-2xl bg-white/[0.05] p-3 flex items-center gap-3">
        <span className="w-9 h-9 rounded-full bg-accent/25 text-white text-sm font-bold flex items-center justify-center flex-shrink-0" aria-hidden="true">{initials}</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-white truncate">{user?.name || 'Signed in'}</p>
          <p className="text-xs text-[#9BBFBF]">{ROLE_LABEL[role] || role} · ID {user?.id}</p>
        </div>
        <button onClick={handleLogout} aria-label="Sign out" title="Sign out"
          className="w-9 h-9 rounded-lg flex items-center justify-center text-[#FF9A9A] hover:bg-white/[0.08] cursor-pointer">
          <LogOut size={18} aria-hidden="true" />
        </button>
      </div>
    </aside>
  )
}
