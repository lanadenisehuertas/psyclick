import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, Activity, Brain, Zap } from 'lucide-react'
import { api } from '../api/psyclick.js'
import { useApp } from '../context/AppContext.jsx'

function MetricRow({ icon: Icon, label, value, color, sub }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-border/50 last:border-0">
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center`}
             style={{ background: `${color}18` }}>
          <Icon size={15} style={{ color }} />
        </div>
        <div>
          <p className="text-sm font-semibold text-tmain">{label}</p>
          {sub && <p className="text-xs text-tsub">{sub}</p>}
        </div>
      </div>
      <p className="text-lg font-bold text-tmain tabular-nums">{value}</p>
    </div>
  )
}

export default function NormativeComplete() {
  const { report, setUser, setClient, setReport, user } = useApp()
  const navigate = useNavigate()

  useEffect(() => {
    api.normativeMode(false)
  }, [])

  const analysis = report?.analysis || {}
  const phq      = report?.phq?.score ?? 0
  const gad      = report?.gad?.score ?? 0
  const t2       = analysis.t2_score  ?? 0
  const psi      = analysis.psi       ?? 0
  const pai      = analysis.pai       ?? 0

  function handleDone() {
    setUser(null)
    setClient(null)
    setReport(null)
    navigate('/')
  }

  return (
    <div className="h-screen bg-bg flex items-center justify-center animate-fade-in p-6">
      <div className="w-full max-w-md">

        {/* Header */}
        <div className="text-center mb-6">
          <div className="w-16 h-16 rounded-full bg-success/15 flex items-center justify-center mx-auto mb-4">
            <CheckCircle size={32} className="text-success" />
          </div>
          <h1 className="text-2xl font-bold text-tmain">Session Complete</h1>
          <p className="text-tsub text-sm mt-1">
            Tester ID: <span className="font-semibold text-tmain">{user?.name}</span>
          </p>
        </div>

        {/* Results card */}
        <div className="bg-white rounded-2xl border border-border shadow-card p-6 mb-4">
          <p className="text-xs font-semibold text-tsub uppercase tracking-widest mb-4">
            Your Biometric Profile
          </p>

          <MetricRow
            icon={Activity}
            label="Hotelling T² Score"
            value={t2.toFixed(3)}
            color="#0ABFBC"
            sub="Overall psychomotor deviation"
          />
          <MetricRow
            icon={Brain}
            label="Psychomotor Stress Index"
            value={psi.toFixed(3)}
            color="#5BA4CF"
            sub="Keystroke-based inhibition marker"
          />
          <MetricRow
            icon={Zap}
            label="Psychomotor Anxiety Index"
            value={pai.toFixed(3)}
            color="#F5A623"
            sub="Cursor-based agitation marker"
          />

          <div className="mt-4 pt-4 border-t border-border/50 grid grid-cols-2 gap-4">
            <div className="text-center">
              <p className="text-xs text-tsub mb-1">PHQ-9</p>
              <p className="text-2xl font-bold text-tmain">{phq}<span className="text-sm font-normal text-tsub">/27</span></p>
            </div>
            <div className="text-center">
              <p className="text-xs text-tsub mb-1">GAD-7</p>
              <p className="text-2xl font-bold text-tmain">{gad}<span className="text-sm font-normal text-tsub">/21</span></p>
            </div>
          </div>
        </div>

        {/* Info note */}
        <div className="bg-accent/8 border border-accent/20 rounded-xl px-4 py-3 mb-5 text-xs text-accent leading-relaxed">
          Your session has been recorded anonymously and will contribute to the normative baseline
          used in clinical comparisons. No individual results are linked to your identity in reports.
        </div>

        <button onClick={handleDone} className="btn-primary w-full text-base">
          Exit Portal
        </button>
      </div>
    </div>
  )
}
