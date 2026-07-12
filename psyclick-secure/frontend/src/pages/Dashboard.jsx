import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, CalendarDays, CheckCircle, AlertTriangle, Search, Plus, Download, X, SlidersHorizontal } from 'lucide-react'
import { format, subDays, parseISO } from 'date-fns'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import Sidebar from '../components/Sidebar.jsx'
import AnimatedBackground from '../components/AnimatedBackground.jsx'
import PasswordDialog from '../components/PasswordDialog.jsx'
import { api }   from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'

// ── Mini sparkline SVG ────────────────────────────────────────────────────────
function Sparkline({ color, bars = [40, 65, 45, 80, 55, 90, 70] }) {
  const max = Math.max(...bars)
  const H = 36, W = 60, gap = 3
  const bw = Math.floor((W - gap * (bars.length - 1)) / bars.length)
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      {bars.map((v, i) => {
        const bh = Math.round((v / max) * H)
        return (
          <rect
            key={i}
            x={i * (bw + gap)}
            y={H - bh}
            width={bw}
            height={bh}
            rx={2}
            fill={color}
            opacity={0.15 + (i / bars.length) * 0.55}
          />
        )
      })}
    </svg>
  )
}

// ── Pharmacy-style stat card ──────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, sub, bg, iconColor, sparkColor, sparkBars, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`rounded-2xl p-5 flex flex-col justify-between cursor-pointer
                  transition-all duration-200 hover:-translate-y-0.5 hover:shadow-hover select-none`}
      style={{ background: bg, minHeight: 140 }}
    >
      <div className="flex items-start justify-between mb-3">
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center`}
             style={{ background: 'rgba(255,255,255,0.6)' }}>
          <Icon size={17} style={{ color: iconColor }} />
        </div>
        <Sparkline color={sparkColor || iconColor} bars={sparkBars} />
      </div>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wider mb-1" style={{ color: iconColor, opacity: 0.7 }}>{label}</p>
        <p className="text-[28px] font-bold leading-none tracking-tight text-tmain">{value ?? '—'}</p>
        {sub && (
          <p className="text-[11px] mt-1.5 font-semibold" style={{ color: iconColor }}>
            {sub}
          </p>
        )}
      </div>
    </div>
  )
}

// ── Custom donut tooltip ──────────────────────────────────────────────────────
function DonutTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0]
  return (
    <div className="bg-tmain text-white text-xs rounded-xl px-3 py-2 shadow-modal">
      <p className="font-bold">{p.name}: {p.value}</p>
    </div>
  )
}

// ── Day abbreviations ─────────────────────────────────────────────────────────
const DAY_ABBR = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']

export default function Dashboard() {
  const { user } = useApp()
  const navigate  = useNavigate()
  const [stats,        setStats]        = useState(null)
  const [sessions,     setSessions]     = useState([])
  const [query,        setQuery]        = useState('')
  const [filterFlag,   setFilterFlag]   = useState('ALL')
  const [exporting,    setExporting]    = useState(false)
  const [showFilters,  setShowFilters]  = useState(false)
  const [showIntakePwd, setShowIntakePwd] = useState(false)

  useEffect(() => {
    const cid = user?.id
    api.stats(cid).then(setStats).catch(() => {})
    api.recentSessions(cid).then(d => setSessions(Array.isArray(d) ? d : [])).catch(() => {})
  }, [user?.id])

  async function handleExportSummary() {
    setExporting(true)
    const res = await api.exportSummary()
    setExporting(false)
    if (res.success && res.file) {
      window.electron?.openExternal?.(`file:///${res.file.replace(/\\/g, '/')}`)
    } else alert(res.error || 'Export failed.')
  }

  // ── Derived chart data ─────────────────────────────────────────────────────
  const filtered = sessions.filter(s => {
    const matchesQuery = !query || s.patient_id?.toLowerCase().includes(query.toLowerCase())
    const matchesFlag  = filterFlag === 'ALL' || s.flag === filterFlag
    return matchesQuery && matchesFlag
  })

  const flagData = [
    { name: 'No Concerns', value: stats?.normal || 0, color: '#36C98E' },
    { name: 'Need Review',  value: stats?.review || 0, color: '#F27C7C' },
  ].filter(d => d.value > 0)

  // Sessions by day (last 7 days)
  const dayBuckets = Array.from({ length: 7 }, (_, i) => {
    const d = subDays(new Date(), 6 - i)
    const key = format(d, 'yyyy-MM-dd')
    const count = sessions.filter(s => (s.timestamp || '').startsWith(key)).length
    return { day: DAY_ABBR[d.getDay()], count }
  })

  // User initials for avatar
  const initials = (user?.name || 'U').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()

  return (
    <div className="h-screen flex bg-[#F0F4F8] overflow-hidden" style={{ position: 'relative' }}>
      <AnimatedBackground variant="subtle" />
      <Sidebar />

      <main className="flex-1 flex flex-col overflow-hidden">

        {/* ── Top bar ─────────────────────────────────────────────────────── */}
        <header className="flex-shrink-0 bg-white border-b border-border px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="flex items-center gap-2 bg-[#F0F4F8] border border-border rounded-xl px-3.5 h-9 w-64
                            focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/15 transition-all">
              <Search size={13} className="text-tsub flex-shrink-0" />
              <input
                className="flex-1 bg-transparent text-sm text-tmain outline-none placeholder:text-tsub min-w-0"
                placeholder="Search clients…"
                value={query}
                onChange={e => setQuery(e.target.value)}
              />
              {query && <button onClick={() => setQuery('')}><X size={12} className="text-tsub" /></button>}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowIntakePwd(true)}
              className="btn-primary text-sm h-9 px-5"
            >
              <Plus size={14} /> New Intake
            </button>
            {/* User avatar chip */}
            <div className="flex items-center gap-2.5 bg-[#F0F4F8] border border-border rounded-xl px-3 h-9 select-none">
              <div className="w-6 h-6 rounded-full bg-accent flex items-center justify-center flex-shrink-0">
                <span className="text-white text-[10px] font-bold">{initials}</span>
              </div>
              <div className="text-right leading-tight">
                <p className="text-xs font-semibold text-tmain truncate max-w-[110px]">{user?.name}</p>
              </div>
            </div>
          </div>
        </header>

        {/* ── Scrollable body ──────────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">

          {/* Welcome + date */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-tmain">
                Welcome, {user?.name ?? 'Clinician'}!
              </h1>
              <p className="text-tsub text-sm mt-0.5">{format(new Date(), "EEEE, d MMMM yyyy")}</p>
            </div>
            <div className="flex items-center gap-2 bg-white border border-border rounded-xl px-4 py-2 text-sm font-medium text-tmain shadow-card">
              <CalendarDays size={14} className="text-accent" />
              All Time
            </div>
          </div>

          {/* ── Section heading ──────────────────────────────────────────── */}
          <div>
            <p className="text-xs font-semibold text-tsub uppercase tracking-widest mb-3">
              Clinical Session Results
            </p>

            {/* Stat cards — pharmacy style */}
            <div className="grid grid-cols-4 gap-4">
              <StatCard
                icon={Users}
                label="Total Clients"
                value={stats?.total ?? '—'}
                sub={`${stats?.total ?? 0} active records`}
                bg="linear-gradient(135deg, #E0F9F9 0%, #CCF4F3 100%)"
                iconColor="#0ABFBC"
                sparkBars={[30,50,40,70,55,80,65]}
                onClick={() => navigate('/clients')}
              />
              <StatCard
                icon={CalendarDays}
                label="Sessions This Week"
                value={stats?.week ?? '—'}
                sub={`+${stats?.week ?? 0} new sessions`}
                bg="linear-gradient(135deg, #EEF4FF 0%, #DDE8FF 100%)"
                iconColor="#5BA4CF"
                sparkBars={[20,40,35,60,45,75,55]}
                onClick={() => navigate('/clients')}
              />
              <StatCard
                icon={CheckCircle}
                label="No Concerns"
                value={stats?.normal ?? '—'}
                sub={stats?.total ? `${Math.round((stats.normal/stats.total)*100)}% of clients` : 'All clear'}
                bg="linear-gradient(135deg, #E8FBF2 0%, #D2F5E5 100%)"
                iconColor="#36C98E"
                sparkBars={[60,75,65,80,70,85,80]}
                onClick={() => navigate('/clients', { state: { filterFlag: 'GREEN' } })}
              />
              <StatCard
                icon={AlertTriangle}
                label="Need Review"
                value={stats?.review ?? '—'}
                sub={stats?.total ? `${Math.round((stats.review/stats.total)*100)}% flagged` : 'Monitor closely'}
                bg="linear-gradient(135deg, #FFF0F0 0%, #FFE0E0 100%)"
                iconColor="#F27C7C"
                sparkBars={[15,25,20,35,28,40,30]}
                onClick={() => navigate('/clients', { state: { filterFlag: 'REVIEW' } })}
              />
            </div>
          </div>

          {/* ── Charts row ───────────────────────────────────────────────── */}
          <div className="grid grid-cols-5 gap-5">

            {/* Donut — flag distribution */}
            <div className="col-span-2 bg-white rounded-2xl border border-border shadow-card p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-tmain">Session Overview</h3>
                <span className="text-xs text-tsub bg-[#F0F4F8] rounded-lg px-2.5 py-1">All time</span>
              </div>
              {flagData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie
                        data={flagData}
                        cx="50%"
                        cy="50%"
                        innerRadius={52}
                        outerRadius={78}
                        paddingAngle={3}
                        dataKey="value"
                        stroke="none"
                      >
                        {flagData.map((d, i) => <Cell key={i} fill={d.color} />)}
                      </Pie>
                      <Tooltip content={<DonutTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  {/* Center label — positioned over SVG */}
                  <div className="flex justify-center gap-4 mt-3">
                    {flagData.map(d => (
                      <div key={d.name} className="flex items-center gap-1.5 text-xs text-tsub">
                        <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: d.color }} />
                        {d.name}
                        <span className="font-bold text-tmain ml-0.5">{d.value}</span>
                      </div>
                    ))}
                  </div>
                  <p className="text-center text-xs text-tsub mt-1">
                    Total <span className="font-bold text-tmain text-sm">{stats?.total ?? 0}</span>
                  </p>
                </>
              ) : (
                <div className="h-[180px] flex items-center justify-center text-tsub text-sm">No data yet</div>
              )}
            </div>

            {/* Bar chart — sessions over last 7 days */}
            <div className="col-span-3 bg-white rounded-2xl border border-border shadow-card p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-tmain">Sessions This Week</h3>
                <span className="text-xs text-tsub bg-[#F0F4F8] rounded-lg px-2.5 py-1">Last 7 days</span>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={dayBuckets} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
                          barSize={24}>
                  <CartesianGrid vertical={false} stroke="#F0F4F8" />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#7A9A9A' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#7A9A9A' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    cursor={{ fill: 'rgba(10,191,188,0.06)', radius: 6 }}
                    contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid #E4F0F0', boxShadow: '0 4px 16px rgba(0,0,0,0.08)' }}
                    formatter={(v) => [v, 'Sessions']}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {dayBuckets.map((d, i) => (
                      <Cell
                        key={i}
                        fill={i === dayBuckets.length - 1 ? '#0ABFBC' : '#D2F0EF'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* ── Recent session table ─────────────────────────────────────── */}
          <div className="bg-white rounded-2xl border border-border shadow-card overflow-hidden">

            {/* Table header — pharmacy feel */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h3 className="text-sm font-bold text-tmain">Recent Session List</h3>
              <div className="flex items-center gap-2">
                {query && (
                  <span className="text-xs text-tsub bg-[#F0F4F8] border border-border rounded-full px-2.5 py-0.5">
                    {filtered.length} result{filtered.length !== 1 ? 's' : ''}
                  </span>
                )}
                <div className="flex items-center gap-2 bg-[#F0F4F8] border border-border rounded-xl px-3 h-8
                                focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/10 transition-all">
                  <Search size={12} className="text-tsub" />
                  <input
                    className="bg-transparent text-xs text-tmain outline-none placeholder:text-tsub w-32"
                    placeholder="Search…"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                  />
                  {query && <button onClick={() => setQuery('')}><X size={11} className="text-tsub" /></button>}
                </div>
                <div className="flex items-center gap-1 relative">
                  <button
                    onClick={() => setShowFilters(v => !v)}
                    className={`h-8 px-2.5 rounded-xl border text-xs font-semibold transition-all ${
                      showFilters || filterFlag !== 'ALL'
                        ? 'bg-accent/10 border-accent/40 text-accent'
                        : 'border-border bg-[#F0F4F8] text-tsub hover:border-accent/30'
                    }`}
                  >
                    <SlidersHorizontal size={12} />
                  </button>
                  {showFilters && (
                    <div className="absolute right-0 top-10 z-20 flex items-center gap-1 bg-white border border-border rounded-xl shadow-modal px-2 py-1.5 animate-fade-up-1">
                      {['ALL','GREEN','AMBER','RED'].map(f => (
                        <button
                          key={f}
                          onClick={() => { setFilterFlag(f); if (f === 'ALL') setShowFilters(false) }}
                          className={`h-7 px-2.5 rounded-lg border text-xs font-semibold transition-all ${
                            filterFlag === f
                              ? f === 'GREEN' ? 'bg-success/15 border-success/40 text-success'
                                : f === 'AMBER' ? 'bg-amber/15 border-amber/40 text-amber'
                                : f === 'RED' ? 'bg-coral/15 border-coral/40 text-coral'
                                : 'bg-accent/10 border-accent/40 text-accent'
                              : 'border-border bg-[#F0F4F8] text-tsub hover:border-accent/30'
                          }`}
                        >
                          {f}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  onClick={handleExportSummary}
                  disabled={exporting}
                  className="flex items-center gap-1.5 h-8 px-3 rounded-xl border border-border bg-[#F0F4F8]
                             text-xs font-medium text-tsub hover:border-accent/40 transition-all disabled:opacity-50"
                >
                  <Download size={12} />
                  {exporting ? 'Exporting…' : 'Export'}
                </button>
                <button onClick={() => navigate('/clients')} className="text-accent text-xs font-semibold hover:underline ml-1">
                  View All →
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[#F8FAFA] border-b border-border">
                    {['Client', 'Date', 'PHQ-9', 'GAD-7', 'Status', 'Summary', ''].map(h => (
                      <th key={h} className="px-5 py-3 text-left text-[11px] font-semibold text-tsub uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center text-tsub py-14 text-sm">
                        {query ? `No clients match "${query}".` : 'No sessions recorded yet.'}
                      </td>
                    </tr>
                  ) : filtered.map((s, i) => {
                    const flagColor = s.flag === 'RED' ? '#FFF0F0' : s.flag === 'AMBER' ? '#FFF8E8' : '#EEFBF5'
                    const flagText  = s.flag === 'RED' ? '#F27C7C' : s.flag === 'AMBER' ? '#F5A623' : '#36C98E'
                    return (
                      <tr
                        key={s.session_id}
                        onClick={() => navigate(`/clients/session/${s.session_id}`)}
                        className={`border-t border-border/40 hover:bg-accent/[0.03] transition-colors cursor-pointer
                                    ${i % 2 === 1 ? 'bg-[#FAFCFC]' : ''}`}
                      >
                        {/* Client */}
                        <td className="px-5 py-3.5">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center
                                            text-accent text-xs font-bold flex-shrink-0">
                              {(s.patient_id || '?')[0].toUpperCase()}
                            </div>
                            <div>
                              <p className="font-semibold text-tmain text-sm leading-tight">{s.patient_id}</p>
                            </div>
                          </div>
                        </td>
                        {/* Date */}
                        <td className="px-5 py-3.5 text-tsub text-xs">{s.timestamp ? new Date(String(s.timestamp).replace(' ', 'T') + 'Z').toLocaleString() : '—'}</td>
                        {/* PHQ */}
                        <td className={`px-5 py-3.5 font-bold text-sm tabular-nums
                                        ${s.phq >= 15 ? 'text-coral' : s.phq >= 10 ? 'text-amber' : 'text-success'}`}>
                          {s.phq ?? '—'}
                        </td>
                        {/* GAD */}
                        <td className={`px-5 py-3.5 font-bold text-sm tabular-nums
                                        ${s.gad >= 15 ? 'text-coral' : s.gad >= 10 ? 'text-amber' : 'text-success'}`}>
                          {s.gad ?? '—'}
                        </td>
                        {/* Status chip */}
                        <td className="px-5 py-3.5">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold"
                                style={{ background: flagColor, color: flagText }}>
                            {s.flag || '—'}
                          </span>
                        </td>
                        {/* Summary */}
                        <td className="px-5 py-3.5 text-xs max-w-[180px] truncate text-tsub">
                          {s.label || '—'}
                        </td>
                        {/* Action */}
                        <td className="px-5 py-3.5 text-right">
                          <span className="text-xs text-accent font-semibold hover:underline">View →</span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </main>

      {showIntakePwd && (
        <PasswordDialog
          onConfirm={() => {
            setShowIntakePwd(false)
            api.auditLog('clinician', 'Opened New Client Intake')
            navigate('/intake')
          }}
          onCancel={() => setShowIntakePwd(false)}
        />
      )}
    </div>
  )
}
