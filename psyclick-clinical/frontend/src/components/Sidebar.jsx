import { NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Users, ClipboardList, LogOut, Cloud, CloudOff, RefreshCw } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../api/psyclick.js'
import PasswordDialog from './PasswordDialog.jsx'
import { useState, useEffect, useCallback } from 'react'

const NAV_SECTIONS = [
  {
    label: 'Main Menu',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    ],
  },
  {
    label: 'Clients',
    items: [
      { to: '/clients', icon: Users,         label: 'Clients' },
      { to: '/audit',   icon: ClipboardList, label: 'Audit'   },
    ],
  },
]

// ── Sync status badge ─────────────────────────────────────────────────────────
function SyncBadge() {
  const [sync,     setSync]     = useState(null)
  const [syncing,  setSyncing]  = useState(false)
  const [tooltip,  setTooltip]  = useState(false)

  const refresh = useCallback(async () => {
    try {
      const res = await fetch('http://127.0.0.1:5001/api/sync/status')
      if (res.ok) setSync(await res.json())
    } catch (_) { /* backend not ready yet */ }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 30_000)
    return () => clearInterval(id)
  }, [refresh])

  async function handleSyncNow(e) {
    e.stopPropagation()
    setSyncing(true)
    try {
      const res = await fetch('http://127.0.0.1:5001/api/sync/now', { method: 'POST' })
      if (res.ok) setSync(await res.json())
    } catch (_) {}
    setSyncing(false)
    setTimeout(refresh, 2000)
  }

  // Not configured — show nothing
  if (!sync || !sync.enabled) return null

  const pending   = sync.pending || 0
  const connected = sync.connected

  let dotColor, label
  if (syncing || sync.syncing) {
    dotColor = '#5BA4CF'; label = 'Syncing…'
  } else if (!connected) {
    dotColor = '#F5A623'; label = pending > 0 ? `${pending} pending — offline` : 'Offline'
  } else if (pending > 0) {
    dotColor = '#F5A623'; label = `${pending} record${pending !== 1 ? 's' : ''} pending`
  } else {
    dotColor = '#36C98E'; label = sync.last_sync ? `Synced ${sync.last_sync.slice(11, 16)}` : 'Synced'
  }

  const Icon = (!connected || pending > 0) ? CloudOff : Cloud

  return (
    <div
      className="relative px-3 pb-3"
      onMouseEnter={() => setTooltip(true)}
      onMouseLeave={() => setTooltip(false)}
    >
      <button
        onClick={handleSyncNow}
        disabled={syncing || sync.syncing}
        className="flex items-center gap-2 w-full px-3 py-2 rounded-xl
                   bg-[#0E2D2D] hover:bg-[#163838] transition-all duration-150
                   text-[11px] font-medium text-[#7ABFBF] disabled:opacity-60"
        title="Click to sync now"
      >
        <span className="relative flex-shrink-0">
          {(syncing || sync.syncing)
            ? <RefreshCw size={13} className="animate-spin" style={{ color: dotColor }} />
            : <Icon size={13} style={{ color: dotColor }} />
          }
          <span
            className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full border border-sidebar"
            style={{ background: dotColor }}
          />
        </span>
        <span className="truncate">{label}</span>
      </button>

      {tooltip && sync.error && (
        <div className="absolute bottom-full left-3 right-3 mb-1 bg-[#1C1C1C] text-white
                        text-[10px] rounded-lg px-2.5 py-2 shadow-modal z-50 leading-tight">
          {sync.error}
        </div>
      )}
    </div>
  )
}

export default function Sidebar({ protected: isProtected = false }) {
  const { setUser } = useApp()
  const navigate    = useNavigate()
  const [showPwd, setShowPwd] = useState(false)
  const [pendingFn, setPendingFn] = useState(null)

  function guard(fn) {
    if (!isProtected) { fn(); return }
    setPendingFn(() => fn)
    setShowPwd(true)
  }

  async function handleLogout() {
    await api.logout()
    setUser(null)
    navigate('/')
  }

  return (
    <>
      <aside className="w-52 flex-shrink-0 h-full flex flex-col bg-sidebar select-none">

        {/* Logo */}
        <div className="px-5 pt-6 pb-5 flex items-center gap-2.5">
          <img
            src={`${import.meta.env.BASE_URL}images/LOGOggg.png`}
            alt="PsyClick"
            className="w-8 h-8 object-contain flex-shrink-0"
          />
          <div>
            <p className="text-white text-sm font-bold leading-tight">PsyClick</p>
            <p className="text-[#4A7070] text-[10px] leading-tight font-medium">Clinical Edition</p>
          </div>
        </div>

        {/* Nav sections */}
        <nav className="flex-1 px-3 overflow-y-auto pb-3 space-y-4">
          {NAV_SECTIONS.map(section => (
            <div key={section.label}>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[#3A6060] px-3 mb-1.5">
                {section.label}
              </p>
              <div className="space-y-0.5">
                {section.items.map(({ to, icon: Icon, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={e => {
                      if (isProtected) {
                        e.preventDefault()
                        guard(() => navigate(to))
                      }
                    }}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium
                       transition-all duration-150 cursor-pointer
                       ${isActive
                         ? 'bg-accent text-white shadow-sm'
                         : 'text-[#7ABFBF] hover:bg-[#1A4040] hover:text-white'}`
                    }
                  >
                    <Icon size={16} />
                    {label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* Divider */}
        <div className="mx-4 h-px bg-[#1A4040] mb-3" />

        {/* Cloud sync status (only visible when Supabase is configured) */}
        <SyncBadge />

        {/* Logout */}
        <div className="px-3 pb-6">
          <button
            onClick={() => guard(handleLogout)}
            className="flex items-center gap-3 w-full px-3.5 py-2.5 rounded-xl text-sm font-medium
                       text-[#FF7070] hover:bg-[#3D1010] transition-all duration-150"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </aside>

      {showPwd && (
        <PasswordDialog
          onConfirm={() => { setShowPwd(false); pendingFn?.() }}
          onCancel={() => setShowPwd(false)}
        />
      )}
    </>
  )
}
