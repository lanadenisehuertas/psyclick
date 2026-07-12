import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { api } from '../api/psyclick.js'
import AnimatedBackground from '../components/AnimatedBackground.jsx'

const CIRCLE_COUNT = 5

function randomPos(existing, areaW, areaH, r = 54) {
  const pad = r + 18
  let pos, tries = 0
  do {
    pos = {
      x: pad + Math.random() * Math.max(1, areaW - pad * 2),
      y: pad + Math.random() * Math.max(1, areaH - pad * 2),
    }
    tries++
  } while (
    tries < 100 &&
    existing.some(e => Math.hypot(e.x - pos.x, e.y - pos.y) < r * 2.5)
  )
  return pos
}

export default function MouseCalibration() {
  const navigate = useNavigate()
  const areaRef = useRef(null)
  const [circles, setCircles] = useState([])
  const [clicked, setClicked] = useState([])
  const [activeIdx, setActiveIdx] = useState(0)
  const [done, setDone] = useState(false)

  useEffect(() => {
    api.mCalStart()
  }, [])

  useEffect(() => {
    function placeCircles() {
      const area = areaRef.current
      if (!area) return
      const { width, height } = area.getBoundingClientRect()
      const pts = []
      for (let i = 0; i < CIRCLE_COUNT; i++) pts.push(randomPos(pts, width, height))
      setCircles(pts)
      setClicked([])
      setActiveIdx(0)
      setDone(false)
    }

    placeCircles()
    window.addEventListener('resize', placeCircles)
    return () => window.removeEventListener('resize', placeCircles)
  }, [])

  function handleCircleClick(idx) {
    if (idx !== activeIdx) return
    const next = [...clicked, idx]
    setClicked(next)
    if (next.length >= CIRCLE_COUNT) {
      setDone(true)
    } else {
      setActiveIdx(activeIdx + 1)
    }
  }

  async function handleNext() {
    await api.mCalSave()
    navigate('/assessment/phq9')
  }

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
            <h1 className="task-title">Click Task</h1>
            <p className="task-subtitle">
              Click each circle in order, numbered 1 to {CIRCLE_COUNT}. Move naturally at your normal pace.
            </p>
          </div>

          <div ref={areaRef} className="card relative min-h-[560px] overflow-hidden">
            <div className="absolute left-0 right-0 top-5 z-10 text-center">
              <span className="rounded-full bg-white/85 px-4 py-2 text-sm font-bold uppercase tracking-wide text-tsub shadow-card">
                {clicked.length} / {CIRCLE_COUNT} clicked
              </span>
            </div>

            <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(10,191,188,0.10),transparent_18rem),radial-gradient(circle_at_80%_70%,rgba(91,164,207,0.12),transparent_20rem)]" />

            {circles.map((c, i) => {
              const isClicked = clicked.includes(i)
              const isActive = i === activeIdx && !done
              const isPending = i > activeIdx

              return (
                <button
                  key={i}
                  onClick={() => handleCircleClick(i)}
                  disabled={isClicked || isPending || done}
                  className="absolute flex h-14 w-14 select-none items-center justify-center rounded-full text-lg font-bold transition-all duration-200"
                  style={{
                    left: c.x - 28,
                    top: c.y - 28,
                    background: isClicked ? '#36C98E' : isActive ? '#0ABFBC' : '#C8E6E6',
                    color: isClicked || isActive ? '#fff' : '#0D2D2D',
                    boxShadow: isActive ? '0 0 0 10px rgba(10,191,188,0.22), 0 18px 35px rgba(10,191,188,0.24)' : 'none',
                    transform: isActive ? 'scale(1.16)' : 'scale(1)',
                    cursor: isPending || done ? 'default' : 'pointer',
                  }}
                >
                  {isClicked ? 'OK' : i + 1}
                </button>
              )
            })}

            {done && (
              <div className="absolute inset-0 flex items-center justify-center bg-white/65 backdrop-blur-sm">
                <div className="rounded-[24px] bg-white p-8 text-center shadow-modal">
                  <p className="mb-1 text-4xl font-bold text-success">All done!</p>
                  <p className="text-lg text-tsub">Click task complete.</p>
                </div>
              </div>
            )}
          </div>

          <button
            onClick={handleNext}
            disabled={!done}
            className="btn-primary h-14 w-full text-lg disabled:cursor-not-allowed disabled:opacity-40"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  )
}
