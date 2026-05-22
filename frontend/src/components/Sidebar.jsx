import { NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Users, ClipboardList, FlaskConical, LogOut } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../api/psyclick.js'
import PasswordDialog from './PasswordDialog.jsx'
import { useState } from 'react'

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
      { to: '/clients', icon: Users,          label: 'Clients' },
      { to: '/audit',   icon: ClipboardList,  label: 'Audit'   },
    ],
  },
  {
    label: 'Research',
    items: [
      { to: '/normative', icon: FlaskConical, label: 'Normative' },
    ],
  },
]

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
            <p className="text-[#4A7070] text-[10px] leading-tight font-medium">Clinical DSS</p>
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
