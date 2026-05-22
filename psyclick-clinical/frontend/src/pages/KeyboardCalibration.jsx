import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { api } from '../api/psyclick.js'
import AnimatedBackground from '../components/AnimatedBackground.jsx'

const TARGET = 'Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce oxygen and energy in the form of sugar. This remarkable biochemical process occurs in the chloroplasts of plant cells.'

export default function KeyboardCalibration() {
  const [typed, setTyped] = useState('')
  const navigate = useNavigate()
  const areaRef = useRef(null)

  useEffect(() => {
    api.kCalStart()
  }, [])

  async function handleNext() {
    await api.kCalSave()
    navigate('/calibration/mouse')
  }

  const pct = Math.min(100, Math.round((typed.length / TARGET.length) * 100))

  return (
    <div className="h-screen overflow-y-auto assessment-bg">
    <AnimatedBackground />
      <div className="task-shell">
        <img src={`${import.meta.env.BASE_URL}images/LOGOggg.png`} alt="PsyClick" className="task-logo" />

        <div className="task-panel">
          <div className="mb-4 text-center relative">
            <button
              onClick={() => navigate('/intake')}
              className="absolute left-0 top-1 flex items-center gap-1.5 text-tsub hover:text-tmain text-sm transition-colors"
            >
              <ArrowLeft size={15} /> Back
            </button>
            <h1 className="task-title">Typing Task</h1>
            <p className="task-subtitle">Please type the text below exactly as shown. Type naturally at your normal pace.</p>
          </div>

          <div className="card p-8">
            <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-tsub">Copy this text</p>
            <p className="text-xl font-semibold leading-relaxed text-blue italic">{TARGET}</p>
          </div>

          <div className="card p-8">
            <p className="mb-4 text-sm font-semibold uppercase tracking-wide text-tsub">Type here</p>
            <textarea
              ref={areaRef}
              className="input-field min-h-[210px] resize-none font-mono text-lg leading-relaxed"
              value={typed}
              onChange={e => setTyped(e.target.value)}
              placeholder="Start typing..."
              autoFocus
            />
            <div className="mt-3 flex items-center justify-between">
              <span className="text-sm font-semibold text-tsub">{typed.length} / {TARGET.length} characters</span>
              <span className="text-sm font-bold text-accent">{pct}% complete</span>
            </div>
            <div className="mt-3 h-3 overflow-hidden rounded-full bg-border">
              <div className="h-full rounded-full bg-accent transition-all duration-300" style={{ width: `${pct}%` }} />
            </div>
          </div>

          <button onClick={handleNext} className="btn-primary h-14 w-full text-lg">
            Continue
          </button>
        </div>
      </div>
    </div>
  )
}
