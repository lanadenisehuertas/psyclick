import { useEffect, useState } from 'react'
import { ClipboardList } from 'lucide-react'
import Sidebar from '../components/Sidebar.jsx'
import { api } from '../api/psyclick.js'

const TABS = [
  { key: 'clinician', label: 'Clinician Activity' },
  { key: 'patient',  label: 'Client Activity'   },
]

const POLL_MS = 10_000   // refresh every 10 seconds while the page is open

export default function Audit() {
  const [actor,   setActor]   = useState('clinician')
  const [logs,    setLogs]    = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    const fetch = (showSpinner) => {
      if (showSpinner) setLoading(true)
      api.auditLogs(actor)
        .then(data => { if (!cancelled) setLogs(Array.isArray(data) ? data : []) })
        .catch(() => { if (!cancelled) setLogs([]) })
        .finally(() => { if (!cancelled && showSpinner) setLoading(false) })
    }

    fetch(true)                               // immediate load (with spinner)
    const timer = setInterval(() => fetch(false), POLL_MS)  // silent background refresh

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [actor])

  return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">

        {/* Header */}
        <header className="px-8 pt-7 pb-4 flex-shrink-0">
          <h1 className="text-2xl font-bold text-tmain">Audit Log</h1>
          <p className="text-tsub text-sm mt-0.5">Full activity trail for compliance and review.</p>
        </header>

        {/* Tab bar */}
        <div className="px-8 mb-4 flex-shrink-0">
          <div className="flex gap-1 bg-white border border-border rounded-xl p-1 w-fit shadow-sm">
            {TABS.map(t => (
              <button
                key={t.key}
                onClick={() => setActor(t.key)}
                className={`px-5 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                  actor === t.key
                    ? 'bg-accent text-white shadow-sm'
                    : 'text-tsub hover:text-tmain'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-8 pb-8">
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#F7FAFA] text-tsub text-xs font-semibold uppercase tracking-wide">
                  {['Timestamp', 'Action', 'Detail'].map(h => (
                    <th key={h} className="px-5 py-3 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={3} className="py-16 text-center">
                      <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                      <p className="text-tsub text-sm">Loading logs…</p>
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="py-16 text-center">
                      <ClipboardList size={36} className="text-border mx-auto mb-3" />
                      <p className="text-tsub text-sm">No audit entries found.</p>
                    </td>
                  </tr>
                ) : logs.map((log, i) => (
                  <tr
                    key={i}
                    className={`border-t border-border/50 ${i % 2 === 1 ? 'bg-[#FAFCFC]' : ''}`}
                  >
                    <td className="px-5 py-3 text-tsub whitespace-nowrap font-mono text-xs">
                      {String(log.timestamp).slice(0, 19)}
                    </td>
                    <td className="px-5 py-3 text-tmain font-medium">{log.action}</td>
                    <td className="px-5 py-3 text-tsub">{log.detail || '—'}</td>
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
