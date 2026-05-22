import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Search, Users, CheckCircle, AlertTriangle, X } from 'lucide-react'
import Sidebar from '../components/Sidebar.jsx'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'

const FLAG_STYLE = {
  GREEN: 'bg-success/15 text-success',
  AMBER: 'bg-amber/15   text-amber',
  RED:   'bg-coral/15   text-coral',
}

const FILTER_LABELS = {
  GREEN:  { label: 'No Concerns',  color: 'bg-success/15 text-success border-success/30' },
  REVIEW: { label: 'Need Review',  color: 'bg-coral/15 text-coral border-coral/30' },
}

export default function Clients() {
  const navigate  = useNavigate()
  const location  = useLocation()
  const { user }  = useApp()
  const [clients, setClients] = useState([])
  const [query,    setQuery]    = useState('')
  const [loading,  setLoading]  = useState(true)

  // Read filter from navigation state (set by Dashboard stat cards)
  const [flagFilter, setFlagFilter] = useState(location.state?.filterFlag || null)

  useEffect(() => {
    api.clients(user?.id)
      .then(data => setClients(Array.isArray(data) ? data : []))
      .catch(() => setClients([]))
      .finally(() => setLoading(false))
  }, [])

  // Clear location state so back-navigation doesn't re-apply filter
  useEffect(() => {
    if (location.state?.filterFlag) {
      window.history.replaceState({}, '')
    }
  }, []) // eslint-disable-line

  const filtered = clients.filter(p => {
    const matchQuery = !query || p.id?.toLowerCase().includes(query.toLowerCase())
    const matchFlag  = !flagFilter
      ? true
      : flagFilter === 'GREEN'
        ? p.flag === 'GREEN'
        : (p.flag === 'RED' || p.flag === 'AMBER')
    return matchQuery && matchFlag
  })

  return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">

        {/* Header */}
        <header className="flex items-center justify-between px-8 pt-7 pb-4 flex-shrink-0">
          <div>
            <h1 className="text-2xl font-bold text-tmain">Client Database</h1>
            <p className="text-tsub text-sm mt-0.5">
              {clients.length} client{clients.length !== 1 ? 's' : ''} on record
              {filtered.length !== clients.length && ` · ${filtered.length} shown`}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Active filter badge */}
            {flagFilter && (
              <button
                onClick={() => setFlagFilter(null)}
                className={`flex items-center gap-1.5 text-xs font-semibold px-3 h-9 rounded-pill border ${FILTER_LABELS[flagFilter]?.color || 'bg-border text-tsub border-border'}`}
              >
                {flagFilter === 'GREEN' ? <CheckCircle size={13} /> : <AlertTriangle size={13} />}
                {FILTER_LABELS[flagFilter]?.label}
                <X size={12} className="ml-0.5 opacity-60" />
              </button>
            )}
            <div className="flex items-center gap-2 bg-white border border-border rounded-pill px-4 h-10 w-60 shadow-sm">
              <Search size={15} className="text-tsub flex-shrink-0" />
              <input
                className="flex-1 bg-transparent text-sm text-tmain outline-none placeholder:text-tsub"
                placeholder="Search by client ID…"
                value={query}
                onChange={e => setQuery(e.target.value)}
              />
              {query && (
                <button onClick={() => setQuery('')}>
                  <X size={14} className="text-tsub hover:text-tmain transition-colors" />
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Filter tabs */}
        <div className="px-8 pb-4 flex gap-2 flex-shrink-0">
          {[
            { key: null,     label: 'All Clients' },
            { key: 'GREEN',  label: 'No Concerns' },
            { key: 'REVIEW', label: 'Need Review' },
          ].map(tab => (
            <button
              key={String(tab.key)}
              onClick={() => setFlagFilter(tab.key)}
              className={`text-xs font-semibold px-4 h-8 rounded-pill border transition-all duration-150 ${
                flagFilter === tab.key
                  ? 'bg-accent text-white border-accent'
                  : 'bg-white text-tsub border-border hover:border-accent/40 hover:text-tmain'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-8 pb-8">
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#F7FAFA] text-tsub text-xs font-semibold uppercase tracking-wide">
                  {['Client ID', 'Total Sessions', 'Last Seen', 'Status', ''].map(h => (
                    <th key={h} className="px-5 py-3 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={5} className="text-center text-tsub py-12">
                      <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                      Loading…
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-16 text-center">
                      <Users size={36} className="text-border mx-auto mb-3" />
                      <p className="text-tsub text-sm">
                        {query || flagFilter ? 'No clients match your filter.' : 'No clients recorded yet.'}
                      </p>
                      {(query || flagFilter) && (
                        <button
                          onClick={() => { setQuery(''); setFlagFilter(null) }}
                          className="mt-3 text-accent text-sm font-medium hover:underline"
                        >
                          Clear filters
                        </button>
                      )}
                    </td>
                  </tr>
                ) : filtered.map((p, i) => (
                  <tr
                    key={p.id}
                    onClick={() => navigate(`/clients/${p.id}`)}
                    className={`border-t border-border/50 hover:bg-accent/5 transition-colors cursor-pointer ${i % 2 === 1 ? 'bg-[#FAFCFC]' : ''}`}
                  >
                    <td className="px-5 py-3 font-semibold text-tmain">{p.id}</td>
                    <td className="px-5 py-3 text-tsub">{p.sessions}</td>
                    <td className="px-5 py-3 text-tsub">{p.last_seen?.slice(0, 16) || '—'}</td>
                    <td className="px-5 py-3">
                      {p.flag ? (
                        <span className={`status-chip ${FLAG_STYLE[p.flag] || 'bg-border text-tsub'}`}>
                          {p.flag}
                        </span>
                      ) : (
                        <span className="text-tsub text-xs">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <button className="text-xs text-accent font-semibold bg-accent/10 rounded-pill px-3 py-1 hover:bg-accent/20 transition-colors">
                        View →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  )
}
