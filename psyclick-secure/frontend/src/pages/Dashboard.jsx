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

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}

function StatCard({ icon, tone, label, value, detail, onClick, delay }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay, ease: EASE }}>
      <ActionCard onClick={onClick} className="w-full p-5 h-full" ariaLabel={`${label}: ${value ?? '—'}. ${detail}`}>
        <div className="flex items-center justify-between">
          <IconTile icon={icon} tone={tone} />
          <ArrowRight size={18} className="text-tsub" aria-hidden="true" />
        </div>
        <p className="mt-4 text-[32px] font-bold text-tmain leading-none tabular-nums">{value ?? '—'}</p>
        <p className="mt-2 font-semibold text-tmain">{label}</p>
        <p className="text-sm text-tsub">{detail}</p>
      </ActionCard>
    </motion.div>
  )
}

const FILTERS = [
  { value: 'ALL', label: 'All' },
  { value: 'ATTENTION', label: 'Needs attention' },
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
  const attention = list
    .filter(s => s.safety || s.flag === 'RED' || s.flag === 'AMBER')
    .sort((a, b) => (b.safety - a.safety) || ((b.flag === 'RED') - (a.flag === 'RED')))
    .slice(0, 5)

  const filtered = list.filter(s => {
    const q = !query || s.patient_id?.toLowerCase().includes(query.trim().toLowerCase())
    const f = filter === 'ALL' || (filter === 'GREEN' ? s.flag === 'GREEN' : (s.flag !== 'GREEN' || s.safety))
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
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, ease: EASE }}>
        <ActionCard onClick={() => navigate('/intake')} ariaLabel="Start a new assessment"
          className="w-full overflow-hidden !border-0 !shadow-none p-0 mb-6">
          <div className="relative rounded-2xl p-7 flex items-center gap-6 text-white"
            style={{ background: 'linear-gradient(120deg, #0B4A49 0%, #087F7D 60%, #0ABFBC 120%)' }}>
            <svg className="absolute right-0 top-0 h-full w-1/2 opacity-25" viewBox="0 0 300 120" preserveAspectRatio="none" aria-hidden="true">
              <path d="M0 80 C 40 30, 70 100, 110 60 S 180 20, 220 70 S 270 90, 300 40" stroke="#B9F2F0" strokeWidth="2" fill="none" />
              <path d="M0 100 C 50 60, 90 110, 140 80 S 210 50, 300 85" stroke="#B9F2F0" strokeWidth="1.2" fill="none" />
            </svg>
            <span className="relative w-14 h-14 rounded-2xl bg-white/15 flex items-center justify-center flex-shrink-0"><Plus size={28} aria-hidden="true" /></span>
            <div className="relative flex-1">
              <p className="text-2xl font-bold">Start a new assessment</p>
              <p className="text-white/80 mt-0.5">About 15 minutes · consent, warm-ups, questionnaires and short written answers.</p>
            </div>
            <span className="relative hidden md:inline-flex items-center gap-2 h-11 px-5 rounded-xl bg-white text-[#0B4A49] font-bold">
              Begin <ArrowRight size={18} aria-hidden="true" />
            </span>
          </div>
        </ActionCard>
      </motion.div>

      {/* Key numbers — each one opens the matching list */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard icon={Users} tone="teal" label="Clients" value={stats?.clients ?? stats?.total}
          detail={`${stats?.total ?? 0} sessions in total`} onClick={() => navigate('/clients')} delay={0.05} />
        <StatCard icon={CalendarDays} tone="blue" label="Sessions this week" value={stats?.week}
          detail="In the last 7 days" onClick={() => navigate('/clients')} delay={0.1} />
        <StatCard icon={AlertTriangle} tone="amber" label="Need follow-up" value={stats?.review}
          detail="Sessions marked Follow up or Review now" onClick={() => setFilter('ATTENTION')} delay={0.15} />
        <StatCard icon={ShieldAlert} tone="coral" label="Self-harm answers" value={stats?.safety ?? 0}
          detail="PHQ-9 question 9 answered above 0" onClick={() => navigate('/clients', { state: { filterFlag: 'SAFETY' } })} delay={0.2} />
      </div>

      <div className="grid xl:grid-cols-[1.4fr_1fr] gap-5 mt-6">
        {/* Worklist */}
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-tmain">Needs your attention</h2>
              <p className="text-sm text-tsub">Self-harm answers first, then Review now and Follow up.</p>
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
                className="w-full flex items-center gap-4 rounded-xl border border-border bg-white px-4 py-3 text-left hover:border-accent/50 hover:bg-[#F7FBFB] transition-colors cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-ink">
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
                <StatusBadge flag={s.flag} label={s.label} />
                <ArrowRight size={18} className="text-tsub" aria-hidden="true" />
              </button>
            ))}
          </div>
        </Card>

        {/* Activity */}
        <Card className="p-6">
          <h2 className="text-lg font-bold text-tmain">This week</h2>
          <p className="text-sm text-tsub">Sessions per day, today highlighted.</p>
          <div className="mt-4 h-[200px]" role="img" aria-label={`Sessions per day: ${week.map(w => `${w.day} ${w.count}`).join(', ')}`}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={week} margin={{ top: 4, right: 4, left: -18, bottom: 0 }} barSize={26}>
                <CartesianGrid vertical={false} stroke="#E8F0F0" />
                <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#557272' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#557272' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip cursor={{ fill: 'rgba(10,191,188,0.06)' }} formatter={(v) => [v, 'Sessions']}
                  contentStyle={{ fontSize: 13, borderRadius: 12, border: '1px solid #E4F0F0' }} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {week.map((d, i) => <Cell key={i} fill={d.today ? '#087F7D' : '#BFE8E7'} />)}
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
            <h2 className="text-lg font-bold text-tmain">Recent sessions</h2>
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
                  className="border-t border-border/70 hover:bg-[#F7FBFB] cursor-pointer transition-colors">
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
