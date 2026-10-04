import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'motion/react'
import { Search, Users, X, Plus, ShieldAlert, ArrowRight, CalendarClock, Layers } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'
import { PageShell, ActionCard, Button, EmptyState, Skeleton, Segmented, EASE } from '../components/ui.jsx'
import { StatusBadge, formatTimestamp } from '../lib/status.jsx'

const FILTER_FROM_STATE = { GREEN: 'GREEN', REVIEW: 'ATTENTION', SAFETY: 'SAFETY' }

export default function Clients() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useApp()
  const [clients, setClients] = useState(null)
  const [query, setQuery]     = useState('')
  const [filter, setFilter]   = useState(FILTER_FROM_STATE[location.state?.filterFlag] || 'ALL')

  useEffect(() => {
    api.clients(user?.id).then(d => setClients(Array.isArray(d) ? d : []))
  }, [user?.id])

  const list = clients || []
  const counts = {
    ALL: list.length,
    RED: list.filter(c => c.flag === 'RED').length,
    AMBER: list.filter(c => c.flag === 'AMBER').length,
    GREEN: list.filter(c => c.flag === 'GREEN').length,
    SAFETY: list.filter(c => c.safety).length,
  }
  counts.ATTENTION = counts.RED + counts.AMBER

  const matches = (c) => {
    if (filter === 'ATTENTION') return c.flag === 'RED' || c.flag === 'AMBER'
    if (filter === 'SAFETY') return c.safety
    return filter === 'ALL' || c.flag === filter
  }
  const filtered = list.filter(c => matches(c) && (!query || c.id.toLowerCase().includes(query.trim().toLowerCase())))

  const options = [
    { value: 'ALL', label: 'All', count: counts.ALL },
    { value: 'RED', label: 'Review now', count: counts.RED },
    { value: 'AMBER', label: 'Follow up', count: counts.AMBER },
    { value: 'GREEN', label: 'No concerns', count: counts.GREEN },
    { value: 'SAFETY', label: 'Self-harm answer', icon: ShieldAlert, count: counts.SAFETY },
  ]
  // "Needs attention" from the dashboard maps onto both flagged groups
  const segValue = filter === 'ATTENTION' ? 'RED' : filter

  return (
    <PageShell
      title="Clients"
      subtitle="Everyone you have assessed. Each card shows the result of their most recent session."
      actions={<Button icon={Plus} onClick={() => navigate('/intake')}>New assessment</Button>}
    >
      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="relative flex-1 min-w-[220px] max-w-sm">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-tsub" aria-hidden="true" />
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search by client code"
            aria-label="Search clients"
            className="w-full h-11 pl-11 pr-10 rounded-xl border border-border bg-white outline-none focus:border-accent-ink focus:ring-4 focus:ring-accent/15" />
          {query && <button onClick={() => setQuery('')} aria-label="Clear search" className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-tsub hover:text-tmain cursor-pointer"><X size={16} aria-hidden="true" /></button>}
        </div>
        <Segmented ariaLabel="Filter clients" value={segValue} onChange={setFilter} options={options} />
      </div>
      {filter === 'ATTENTION' && (
        <p className="text-sm text-tsub -mt-2 mb-4">Showing clients whose latest result is Review now or Follow up. <button className="text-accent-ink font-semibold hover:underline cursor-pointer" onClick={() => setFilter('ALL')}>Show all</button></p>
      )}

      {clients === null ? (
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">{[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-[150px]" />)}</div>
      ) : list.length === 0 ? (
        <div className="bg-white rounded-2xl border border-border">
          <EmptyState icon={Users} title="No clients yet" action={<Button icon={Plus} onClick={() => navigate('/intake')}>Start the first assessment</Button>}>
            Clients appear here after their first completed assessment.
          </EmptyState>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-border">
          <EmptyState icon={Search} title="No clients match" action={<Button variant="secondary" onClick={() => { setQuery(''); setFilter('ALL') }}>Clear search and filters</Button>}>
            Try another code or a different filter.
          </EmptyState>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((c, i) => (
            <motion.div key={c.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25, delay: Math.min(i, 8) * 0.03, ease: EASE }}>
              <ActionCard onClick={() => navigate(`/clients/${c.id}`)} className="w-full p-5" ariaLabel={`Open client ${c.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="w-11 h-11 rounded-full bg-accent/10 text-accent-ink font-bold flex items-center justify-center" aria-hidden="true">{c.id.slice(-2)}</span>
                    <div>
                      <p className="font-mono text-lg font-semibold text-tmain">{c.id}</p>
                      <p className="text-sm text-tsub">Latest result</p>
                    </div>
                  </div>
                  {c.flag ? <StatusBadge flag={c.flag} /> : <span className="text-sm text-tsub">—</span>}
                </div>
                {c.safety && (
                  <p className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-coral/10 text-coral-ink text-xs font-semibold px-2.5 py-1">
                    <ShieldAlert size={13} aria-hidden="true" /> Self-harm answer on record
                  </p>
                )}
                <div className="mt-4 pt-4 border-t border-border flex items-center justify-between text-sm text-tsub">
                  <span className="inline-flex items-center gap-1.5"><Layers size={15} aria-hidden="true" />{c.sessions} session{c.sessions !== 1 ? 's' : ''}</span>
                  <span className="inline-flex items-center gap-1.5"><CalendarClock size={15} aria-hidden="true" />{formatTimestamp(c.last_seen, { dateStyle: 'medium' })}</span>
                  <ArrowRight size={16} className="text-accent-ink" aria-hidden="true" />
                </div>
              </ActionCard>
            </motion.div>
          ))}
        </div>
      )}
    </PageShell>
  )
}
