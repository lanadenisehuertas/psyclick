import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { format, subDays } from 'date-fns'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts'
import { Users, CalendarDays, AlertTriangle, ShieldAlert, Plus, ArrowRight, Search, Download, X, CheckCircle2, Inbox } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import { PageShell, Card, ActionCard, Button, IconTile, EmptyState, Skeleton, Segmented, useToast, EASE } from '../components/ui.jsx'
import { StatusBadge, formatTimestamp, parseTimestamp } from '../lib/status.jsx'
import { TINT } from '../report/overview.jsx'

const ALERT_TINT = { bg: 'linear-gradient(150deg,#FBE1DF 0%,#FDF4F3 70%)', ink: '#B83A38' }

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}

function StatCard({ label, value, detail, onClick, delay, alert, tint = 'mint', icon: Icon }) {
  const t = alert && value > 0 ? ALERT_TINT : TINT[tint]
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay, ease: EASE }}>
      <ActionCard onClick={onClick} style={{ background: t.bg }}
        className={`w-full p-5 h-full group flex flex-col justify-start !border-white/70 ${alert && value > 0 ? 'ring-2 ring-[#F27C7C]/70' : ''}`}
        ariaLabel={`${label}: ${value ?? '—'}. ${detail}`}>
        <p className="text-sm font-semibold text-tmain flex items-start justify-between gap-2">
          {label}
          {Icon && (
            <span className="w-10 h-10 -mt-1 -mr-1 rounded-full bg-white/90 border border-white shadow-sm flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-105" style={{ color: t.ink }}>
              <Icon size={19} aria-hidden="true" />
            </span>
          )}
        </p>
        <p className={`mt-1 font-display text-[40px] font-semibold leading-none tabular-nums ${alert && value > 0 ? 'text-coral-ink' : 'text-tmain'}`}>{value ?? '—'}</p>
        <p className="mt-3 text-sm text-tsub flex items-center justify-between gap-2">{detail}
          <ArrowRight size={16} className="opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all flex-shrink-0" style={{ color: t.ink }} aria-hidden="true" /></p>
      </ActionCard>
    </motion.div>
  )
}

const FILTERS = [
  { value: 'ALL', label: 'All' },
  { value: 'ATTENTION', label: 'Needs attention' },
  { value: 'REPEAT', label: 'To repeat' },
  { value: 'GREEN', label: 'No concerns' },
]

export default function Dashboard() {
  const { user } = useApp()
  const navigate = useNavigate()
  const toast = useToast()
  const [stats, setStats]       = useState(null)
  const [sessions, setSessions] = useState(null)
  const [query, setQuery]       = useState('')
  const [filter, setFilter]     = useState('ALL')
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    const cid = user?.id
    api.stats(cid).then(d => setStats(d?.error ? null : d))
    api.recentSessions(cid).then(d => setSessions(Array.isArray(d) ? d : []))
  }, [user?.id])

  async function handleExportSummary() {
    setExporting(true)
    const res = await api.exportSummary()
    setExporting(false)
    if (res.success && res.file) {
      toast('Encrypted summary saved.')
      window.electron?.openExternal?.(`file:///${res.file.replace(/\\/g, '/')}`)
    } else toast(res.error || 'Export failed. Please try again.', 'error')
  }

  const list = sessions || []
  // A low result whose questionnaire may not be reliable (rushed or one answer throughout)
  const needsCheck = s => (s.check || []).length > 0 && (s.flag === 'GREEN' || s.flag === 'REPEAT')
  const attention = list
    .filter(s => s.safety || s.flag === 'RED' || s.flag === 'AMBER' || needsCheck(s))
    .sort((a, b) => (b.safety - a.safety) || ((b.flag === 'RED') - (a.flag === 'RED')) || (needsCheck(a) - needsCheck(b)))
    .slice(0, 5)

  const filtered = list.filter(s => {
    const q = !query || s.patient_id?.toLowerCase().includes(query.trim().toLowerCase())
    const f = filter === 'ALL' || (filter === 'GREEN' ? s.flag === 'GREEN'
      : filter === 'REPEAT' ? s.flag === 'REPEAT'
      : (s.flag === 'RED' || s.flag === 'AMBER' || s.safety))
    return q && f
  })

  // Sessions per day for the last 7 days, using the local calendar day
  const week = useMemo(() => Array.from({ length: 7 }, (_, i) => {
    const d = subDays(new Date(), 6 - i)
    const key = format(d, 'yyyy-MM-dd')
    const count = list.filter(s => { const t = parseTimestamp(s.timestamp); return t && format(t, 'yyyy-MM-dd') === key }).length
    return { day: format(d, 'EEE'), count, today: i === 6 }
  }), [list])

  const firstName = (user?.name || '').replace(/^(Dr\.?|Dra\.?)\s+/i, '').split(' ')[0] || 'there'

  return (
    <PageShell
      eyebrow={format(new Date(), 'EEEE, d MMMM yyyy')}
      title={`${greeting()}, ${firstName}`}
      subtitle="Here is what needs your attention today."
    >
      {/* Primary action */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: EASE }}
        className="mb-6 rounded-[20px] bg-brand px-6 py-5 flex flex-wrap items-center gap-5 relative overflow-hidden shadow-[0_18px_40px_-20px_rgba(61,95,168,0.55),inset_0_1px_0_rgba(255,255,255,0.6)]">
        <svg className="absolute inset-0 w-full h-full opacity-40" preserveAspectRatio="none" viewBox="0 0 600 120" aria-hidden="true">
          <path d="M0 70 C 60 30, 110 110, 170 60 S 290 20, 350 70 S 470 100, 600 50" fill="none" stroke="#fff" strokeWidth="1.5" />
          <path d="M0 95 C 80 70, 140 120, 220 85 S 380 60, 600 90" fill="none" stroke="#fff" strokeWidth="1" />
        </svg>
        <svg width="132" height="40" viewBox="0 0 132 40" aria-hidden="true" className="flex-shrink-0 relative">
          <path d="M0 26 H18 L24 10 L31 34 L38 18 L46 24 H62 L68 6 L76 36 L83 20 L90 26 H132" fill="none" stroke="#0F2A33" strokeWidth="2.2" strokeLinejoin="round" />
        </svg>
        <div className="flex-1 min-w-[240px] relative">
          <p className="font-display text-xl font-semibold text-tmain">Start a new assessment</p>
          <p className="text-tmain/80">About 15 minutes: consent, two warm-ups, two questionnaires and twelve short written answers.</p>
        </div>
        <Button size="lg" iconRight={ArrowRight} onClick={() => navigate('/intake')} className="relative !bg-[#0F2A33] hover:!bg-[#173C48]">Begin</Button>
      </motion.div>

      {/* Key numbers — each one opens the matching list */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard tint="mint" icon={Users} label="Clients" value={stats?.clients ?? stats?.total}
          detail={`${stats?.total ?? 0} sessions in total`} onClick={() => navigate('/clients')} delay={0.05} />
        <StatCard tint="cyan" icon={CalendarDays} label="Sessions this week" value={stats?.week}
          detail="In the last 7 days" onClick={() => navigate('/clients')} delay={0.1} />
        <StatCard tint="peri" icon={AlertTriangle} label="Need follow-up" value={stats?.review}
          detail={stats?.repeat ? `Follow up or Review now · ${stats.repeat} more to repeat (too little typing)` : 'Sessions marked Follow up or Review now'}
          onClick={() => setFilter('ATTENTION')} delay={0.15} />
        <StatCard alert tint="deep" icon={ShieldAlert} label="Self-harm answers" value={stats?.safety ?? 0}
          detail="PHQ-9 question 9 answered above 0" onClick={() => navigate('/clients', { state: { filterFlag: 'SAFETY' } })} delay={0.2} />
      </div>

      <div className="grid xl:grid-cols-[1.4fr_1fr] gap-5 mt-6">
        {/* Worklist */}
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-lg font-semibold text-tmain">Needs your attention</h2>
              <p className="text-sm text-tsub">Self-harm answers first, then Review now, Follow up, and questionnaires to check.</p>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            {sessions === null ? (
              [0, 1, 2].map(i => <Skeleton key={i} className="h-[68px]" />)
            ) : attention.length === 0 ? (
              <div className="flex items-center gap-3 rounded-xl bg-success/10 border border-success/30 p-4 text-success-ink">
                <CheckCircle2 size={22} aria-hidden="true" />
                <p className="font-semibold">Nothing needs attention right now.</p>
              </div>
            ) : attention.map(s => (
              <button key={s.session_id} onClick={() => navigate(`/clients/session/${s.session_id}`)}
                className="w-full flex items-center gap-4 rounded-xl border border-border bg-white px-4 py-3 text-left hover:border-accent/50 hover:bg-[#F4FAFB] transition-colors cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-ink">
                <span className="w-10 h-10 rounded-full bg-accent/10 text-accent-ink font-bold flex items-center justify-center flex-shrink-0" aria-hidden="true">{(s.patient_id || '?').slice(-2)}</span>
                <span className="flex-1 min-w-0">
                  <span className="block font-semibold text-tmain">{s.patient_id}</span>
                  <span className="block text-sm text-tsub truncate">{formatTimestamp(s.timestamp)} · PHQ-9 {s.phq} · GAD-7 {s.gad}</span>
                </span>
                {s.safety && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-coral-ink text-white text-xs font-semibold px-2.5 py-1">
                    <ShieldAlert size={13} aria-hidden="true" /> Self-harm answer
                  </span>
                )}
                {needsCheck(s) && (
                  <span className="inline-flex items-center rounded-full bg-amber/15 text-amber-ink border border-amber/40 text-xs font-semibold px-2.5 py-0.5 whitespace-nowrap">Check questionnaire</span>
                )}
                <StatusBadge flag={s.flag} label={s.label} />
                <ArrowRight size={18} className="text-tsub" aria-hidden="true" />
              </button>
            ))}
          </div>
        </Card>

        {/* Activity */}
        <Card className="p-6">
          <h2 className="font-display text-lg font-semibold text-tmain">This week</h2>
          <p className="text-sm text-tsub">Sessions per day, today highlighted.</p>
          <div className="mt-4 h-[200px]" role="img" aria-label={`Sessions per day: ${week.map(w => `${w.day} ${w.count}`).join(', ')}`}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={week} margin={{ top: 4, right: 4, left: -18, bottom: 0 }} barSize={26}>
                <defs>
                  <linearGradient id="wk-today" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0" stopColor="#68D8E8" /><stop offset="1" stopColor="#3D5FA8" />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="#E3EDF0" />
                <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#4A6670' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#4A6670' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip cursor={{ fill: 'rgba(104,216,232,0.10)' }} formatter={(v) => [v, 'Sessions']}
                  contentStyle={{ fontSize: 13, borderRadius: 12, border: '1px solid #D9E6EA' }} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {week.map((d, i) => <Cell key={i} fill={d.today ? 'url(#wk-today)' : '#BDEBE0'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Recent sessions */}
      <Card className="mt-6 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-5 border-b border-border">
          <div>
            <h2 className="font-display text-lg font-semibold text-tmain">Recent sessions</h2>
            <p className="text-sm text-tsub">Your 12 most recent assessments. Open one to see the full report.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-tsub" aria-hidden="true" />
              <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search client code" aria-label="Search sessions by client code"
                className="h-9 w-52 pl-9 pr-8 rounded-xl border border-border bg-white text-sm outline-none focus:border-accent-ink focus:ring-4 focus:ring-accent/15" />
              {query && <button onClick={() => setQuery('')} aria-label="Clear search" className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-tsub hover:text-tmain cursor-pointer"><X size={14} aria-hidden="true" /></button>}
            </div>
            <Segmented ariaLabel="Session filter" value={filter} onChange={setFilter} options={FILTERS} />
            <Button variant="secondary" size="sm" icon={Download} loading={exporting} onClick={handleExportSummary}>Export summary</Button>
          </div>
        </div>
        {sessions === null ? (
          <div className="p-6 space-y-2">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-12" />)}</div>
        ) : list.length === 0 ? (
          <EmptyState icon={Inbox} title="No sessions yet"
            action={<Button icon={Plus} onClick={() => navigate('/intake')}>Start the first assessment</Button>}>
            Completed assessments will appear here with their result.
          </EmptyState>
        ) : filtered.length === 0 ? (
          <EmptyState icon={Search} title="No matching sessions"
            action={<Button variant="secondary" onClick={() => { setQuery(''); setFilter('ALL') }}>Clear search and filters</Button>}>
            Try another client code or filter.
          </EmptyState>
        ) : (
          <table className="w-full">
            <caption className="sr-only">Recent sessions</caption>
            <thead>
              <tr className="text-left text-xs font-semibold uppercase tracking-wider text-tsub bg-[#F7FAFA]">
                <th scope="col" className="px-6 py-3">Client</th>
                <th scope="col" className="px-4 py-3">Date</th>
                <th scope="col" className="px-4 py-3">PHQ-9</th>
                <th scope="col" className="px-4 py-3">GAD-7</th>
                <th scope="col" className="px-4 py-3">Result</th>
                <th scope="col" className="px-6 py-3"><span className="sr-only">Open</span></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(s => (
                <tr key={s.session_id} onClick={() => navigate(`/clients/session/${s.session_id}`)}
                  className="border-t border-border/70 hover:bg-[#F4FAFB] cursor-pointer transition-colors">
                  <td className="px-6 py-3.5 font-semibold text-tmain">
                    <span className="inline-flex items-center gap-2">
                      {s.patient_id}
                      {s.safety && <ShieldAlert size={16} className="text-coral-ink" aria-label="Self-harm answer" />}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-tsub">{formatTimestamp(s.timestamp)}</td>
                  <td className="px-4 py-3.5 tabular-nums font-semibold text-tmain">{s.phq}</td>
                  <td className="px-4 py-3.5 tabular-nums font-semibold text-tmain">{s.gad}</td>
                  <td className="px-4 py-3.5"><StatusBadge flag={s.flag} label={s.label} /></td>
                  <td className="px-6 py-3.5 text-right">
                    <button onClick={(e) => { e.stopPropagation(); navigate(`/clients/session/${s.session_id}`) }}
                      className="inline-flex items-center gap-1 text-sm font-semibold text-accent-ink hover:underline cursor-pointer">
                      Open report <ArrowRight size={15} aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </PageShell>
  )
}
