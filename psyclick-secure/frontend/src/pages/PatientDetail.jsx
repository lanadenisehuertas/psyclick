import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CalendarDays, Trash2, Activity, Brain, AlertTriangle, CheckCircle } from 'lucide-react'
import Sidebar from '../components/Sidebar.jsx'
import PasswordDialog from '../components/PasswordDialog.jsx'
import { api } from '../api/psyclick.js'

const FLAG_STYLE = {
  GREEN: { chip: 'bg-success/15 text-success', icon: CheckCircle,  label: 'No Concerns'    },
  AMBER: { chip: 'bg-amber/15 text-amber',      icon: AlertTriangle, label: 'Moderate Risk'  },
  RED:   { chip: 'bg-coral/15 text-coral',       icon: AlertTriangle, label: 'Needs Review'  },
}

function phqLabel(s) {
  if (s == null) return '—'
  if (s <= 4)  return 'Minimal'
  if (s <= 9)  return 'Mild'
  if (s <= 14) return 'Moderate'
  if (s <= 19) return 'Mod-Severe'
  return 'Severe'
}
function gadLabel(s) {
  if (s == null) return '—'
  if (s <= 4)  return 'Minimal'
  if (s <= 9)  return 'Mild'
  if (s <= 14) return 'Moderate'
  return 'Severe'
}

export default function ClientDetail() {
  const { clientId } = useParams()
  const navigate      = useNavigate()
  const [sessions,   setSessions]   = useState([])
  const [loading,    setLoading]    = useState(true)
  const [deleting,   setDeleting]   = useState(false)
  const [confirmDel, setConfirmDel] = useState(false)
  const [showPwd,    setShowPwd]    = useState(false)

  useEffect(() => {
    if (!clientId) return
    api.clientSessions(clientId)
      .then(data => setSessions(Array.isArray(data) ? data : []))
      .catch(() => setSessions([]))
      .finally(() => setLoading(false))
  }, [clientId])

  async function handleDelete() {
    setDeleting(true)
    const res = await api.deleteClient(clientId)
    setDeleting(false)
    if (res.success) navigate('/clients')
    else alert(res.error || 'Failed to delete record.')
  }

  // Derived summary stats
  const latestFlag  = sessions[0]?.flag || null
  const latestPHQ   = sessions[0]?.phq  ?? null
  const latestGAD   = sessions[0]?.gad  ?? null
  const latestLabel = sessions[0]?.label || ''
  const flagCounts  = sessions.reduce((acc, s) => {
    if (s.flag) acc[s.flag] = (acc[s.flag] || 0) + 1
    return acc
  }, {})
  const fs = latestFlag ? FLAG_STYLE[latestFlag] : null
  const FlagIcon = fs?.icon || CheckCircle

  return (
    <div className="h-screen flex bg-bg">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">

        {/* Header */}
        <header className="px-8 pt-7 pb-4 flex-shrink-0 border-b border-border/50">
          <button
            onClick={() => navigate('/clients')}
            className="flex items-center gap-2 text-tsub hover:text-tmain text-sm mb-5 transition-colors"
          >
            <ArrowLeft size={16} /> Back to Client Database
          </button>
          <div className="flex items-center gap-4">
            <div className={`w-13 h-13 rounded-full flex items-center justify-center text-lg font-bold
              ${latestFlag === 'RED' ? 'bg-coral/15 text-coral' : latestFlag === 'AMBER' ? 'bg-amber/15 text-amber' : 'bg-accent/15 text-accent'}`}
              style={{ width: 52, height: 52 }}>
              {clientId?.[0]?.toUpperCase() || 'C'}
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl font-bold text-tmain truncate">{clientId}</h1>
              <p className="text-tsub text-sm mt-0.5">
                {loading ? 'Loading…' : `${sessions.length} session${sessions.length !== 1 ? 's' : ''} on record`}
                {latestLabel ? <span className="ml-3 text-tsub">· {latestLabel}</span> : null}
              </p>
            </div>
            <button
              onClick={() => setShowPwd(true)}
              className="flex items-center gap-2 text-sm font-medium text-coral border border-coral/30 bg-coral/10
                         hover:bg-coral/20 rounded-xl px-4 h-9 transition-all duration-150 flex-shrink-0"
            >
              <Trash2 size={14} /> Delete Record
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-8 py-6 space-y-5">

          {/* Summary stat row */}
          {!loading && sessions.length > 0 && (
            <div className="grid grid-cols-4 gap-4">
              {/* Overall flag */}
              <div className={`card p-5 flex flex-col gap-2 ${latestFlag === 'RED' ? 'border-coral/40' : latestFlag === 'AMBER' ? 'border-amber/40' : 'border-success/40'}`}>
                <div className="flex items-center gap-2">
                  <FlagIcon size={16} className={fs ? fs.chip.split(' ')[1] : 'text-tsub'} />
                  <p className="text-xs font-semibold text-tsub uppercase tracking-wide">Latest Status</p>
                </div>
                <p className={`text-base font-bold ${fs ? fs.chip.split(' ')[1] : 'text-tsub'}`}>
                  {fs?.label || '—'}
                </p>
                <div className="flex gap-2 flex-wrap mt-1">
                  {Object.entries(flagCounts).map(([f, n]) => (
                    <span key={f} className={`text-xs px-2 py-0.5 rounded-full font-medium ${FLAG_STYLE[f]?.chip || 'bg-border text-tsub'}`}>
                      {n}× {f}
                    </span>
                  ))}
                </div>
              </div>

              {/* PHQ-9 */}
              <div className="card p-5 flex flex-col gap-2">
                <p className="text-xs font-semibold text-tsub uppercase tracking-wide">PHQ-9 (Latest)</p>
                <p className={`text-3xl font-bold ${latestPHQ >= 15 ? 'text-coral' : latestPHQ >= 10 ? 'text-amber' : 'text-success'}`}>
                  {latestPHQ ?? '—'}
                  {latestPHQ != null && <span className="text-sm font-normal text-tsub ml-1">/ 27</span>}
                </p>
                <p className={`text-xs font-medium ${latestPHQ >= 15 ? 'text-coral' : latestPHQ >= 10 ? 'text-amber' : 'text-success'}`}>
                  {phqLabel(latestPHQ)}
                </p>
              </div>

              {/* GAD-7 */}
              <div className="card p-5 flex flex-col gap-2">
                <p className="text-xs font-semibold text-tsub uppercase tracking-wide">GAD-7 (Latest)</p>
                <p className={`text-3xl font-bold ${latestGAD >= 15 ? 'text-coral' : latestGAD >= 10 ? 'text-amber' : 'text-success'}`}>
                  {latestGAD ?? '—'}
                  {latestGAD != null && <span className="text-sm font-normal text-tsub ml-1">/ 21</span>}
                </p>
                <p className={`text-xs font-medium ${latestGAD >= 15 ? 'text-coral' : latestGAD >= 10 ? 'text-amber' : 'text-success'}`}>
                  {gadLabel(latestGAD)}
                </p>
              </div>

              {/* Biometric trend */}
              <div className="card p-5 flex flex-col gap-2">
                <p className="text-xs font-semibold text-tsub uppercase tracking-wide">Biometric (Latest)</p>
                <div className="flex gap-4 mt-1">
                  <div>
                    <p className="text-xs text-tsub">PSI</p>
                    <p className={`text-xl font-bold ${(sessions[0]?.psi ?? 0) >= 2 ? 'text-coral' : (sessions[0]?.psi ?? 0) >= 0.5 ? 'text-amber' : 'text-success'}`}>
                      {sessions[0]?.psi != null ? Number(sessions[0].psi).toFixed(2) : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-tsub">PAI</p>
                    <p className={`text-xl font-bold ${(sessions[0]?.pai ?? 0) >= 2 ? 'text-coral' : (sessions[0]?.pai ?? 0) >= 0.5 ? 'text-amber' : 'text-success'}`}>
                      {sessions[0]?.pai != null ? Number(sessions[0].pai).toFixed(2) : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-tsub">T²</p>
                    <p className="text-xl font-bold text-tmain">
                      {sessions[0]?.t2 != null ? Number(sessions[0].t2).toFixed(2) : '—'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Sessions table */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <h2 className="font-bold text-tmain">Session History</h2>
              {!loading && sessions.length > 0 && (
                <span className="text-xs text-tsub">{sessions.length} session{sessions.length !== 1 ? 's' : ''}</span>
              )}
            </div>

            {loading ? (
              <div className="py-16 text-center">
                <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className="text-tsub text-sm">Loading sessions…</p>
              </div>
            ) : sessions.length === 0 ? (
              <div className="py-16 text-center">
                <CalendarDays size={36} className="text-border mx-auto mb-3" />
                <p className="text-tsub text-sm">No sessions found for this client.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-[#F7FAFA] text-tsub text-xs font-semibold uppercase tracking-wide">
                      {['#', 'Date', 'PHQ-9', 'GAD-7', 'T²', 'PSI', 'PAI', 'Summary', 'Status', ''].map(h => (
                        <th key={h} className="px-5 py-3 text-left whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map((s, i) => {
                      const fs2 = s.flag ? FLAG_STYLE[s.flag] : null
                      return (
                        <tr
                          key={s.session_id}
                          onClick={() => navigate(`/clients/session/${s.session_id}`)}
                          className={`border-t border-border/50 hover:bg-accent/5 transition-colors cursor-pointer ${i % 2 === 1 ? 'bg-[#FAFCFC]' : ''}`}
                        >
                          <td className="px-5 py-3 font-medium text-tsub text-xs">#{s.session_id}</td>
                          <td className="px-5 py-3 text-tsub whitespace-nowrap">{s.timestamp}</td>
                          <td className={`px-5 py-3 font-bold ${(s.phq ?? 0) >= 15 ? 'text-coral' : (s.phq ?? 0) >= 10 ? 'text-amber' : 'text-success'}`}>
                            {s.phq ?? '—'}
                          </td>
                          <td className={`px-5 py-3 font-bold ${(s.gad ?? 0) >= 15 ? 'text-coral' : (s.gad ?? 0) >= 10 ? 'text-amber' : 'text-success'}`}>
                            {s.gad ?? '—'}
                          </td>
                          <td className="px-5 py-3 font-mono text-xs text-tmain">{s.t2 != null ? Number(s.t2).toFixed(2) : '—'}</td>
                          <td className={`px-5 py-3 font-mono text-xs ${(s.psi ?? 0) >= 2 ? 'text-coral' : (s.psi ?? 0) >= 0.5 ? 'text-amber' : 'text-success'}`}>
                            {s.psi != null ? Number(s.psi).toFixed(2) : '—'}
                          </td>
                          <td className={`px-5 py-3 font-mono text-xs ${(s.pai ?? 0) >= 2 ? 'text-coral' : (s.pai ?? 0) >= 0.5 ? 'text-amber' : 'text-success'}`}>
                            {s.pai != null ? Number(s.pai).toFixed(2) : '—'}
                          </td>
                          <td className="px-5 py-3 text-tsub text-xs max-w-[180px] truncate">{s.label || '—'}</td>
                          <td className="px-5 py-3">
                            {s.flag ? (
                              <span className={`status-chip ${fs2?.chip || 'bg-border text-tsub'}`}>{s.flag}</span>
                            ) : (
                              <span className="text-tsub text-xs">—</span>
                            )}
                          </td>
                          <td className="px-5 py-3">
                            <button className="text-xs text-accent font-semibold bg-accent/10 rounded-pill px-3 py-1 hover:bg-accent/20 transition-colors whitespace-nowrap">
                              View Report →
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Password verification before delete confirmation */}
      {showPwd && (
        <PasswordDialog
          onConfirm={() => { setShowPwd(false); setConfirmDel(true) }}
          onCancel={() => setShowPwd(false)}
        />
      )}

      {/* Delete confirmation modal */}
      {confirmDel && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-card shadow-modal p-8 w-full max-w-md animate-slide-up">
            <div className="w-12 h-12 rounded-full bg-coral/15 flex items-center justify-center mx-auto mb-4">
              <Trash2 size={22} className="text-coral" />
            </div>
            <h2 className="text-xl font-bold text-tmain text-center mb-2">Delete Client Record?</h2>
            <p className="text-tsub text-sm text-center mb-6 leading-relaxed">
              This will permanently delete <span className="font-semibold text-tmain">{clientId}</span> and all
              their sessions ({sessions.length} record{sessions.length !== 1 ? 's' : ''}). This cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDel(false)}
                className="flex-1 h-11 rounded-xl border border-border text-tmain text-sm font-medium hover:bg-bg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { setConfirmDel(false); handleDelete() }}
                disabled={deleting}
                className="flex-1 h-11 rounded-xl bg-coral text-white text-sm font-semibold hover:bg-red-500 transition-colors disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Yes, Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
