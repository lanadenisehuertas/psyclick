import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import { ArrowRight, Check, RotateCcw } from 'lucide-react'
import { api } from '../api/psyclick.js'
import AssessmentShell, { StepHeading, useStepStart } from '../components/AssessmentShell.jsx'
import { Button, Alert } from '../components/ui.jsx'

const CIRCLE_COUNT = 5

function randomPos(existing, areaW, areaH, r = 54) {
  const pad = r + 18
  let pos, tries = 0
  do {
    pos = {
      x: pad + Math.random() * Math.max(1, areaW - pad * 2),
      y: pad + 40 + Math.random() * Math.max(1, areaH - pad * 2 - 40),
    }
    tries++
  } while (tries < 100 && existing.some(e => Math.hypot(e.x - pos.x, e.y - pos.y) < r * 2.5))
  return pos
}

export default function MouseCalibration() {
  const navigate = useNavigate()
  const areaRef = useRef(null)
  const [circles, setCircles]     = useState([])
  const [clicked, setClicked]     = useState([])
  const [activeIdx, setActiveIdx] = useState(0)
  const [done, setDone]           = useState(false)
  const [busy, setBusy]           = useState(false)
  const [err, setErr]             = useState('')

  function placeCircles() {
    const area = areaRef.current
    if (!area) return
    const { width, height } = area.getBoundingClientRect()
    const pts = []
    for (let i = 0; i < CIRCLE_COUNT; i++) pts.push(randomPos(pts, width, height))
    setCircles(pts); setClicked([]); setActiveIdx(0); setDone(false)
  }

  const lost = useStepStart(api.mCalStart)
  useEffect(() => {
    placeCircles()
    window.addEventListener('resize', placeCircles)
    return () => window.removeEventListener('resize', placeCircles)
  }, [])

  function handleCircleClick(idx) {
    if (idx !== activeIdx) return
    const next = [...clicked, idx]
    setClicked(next)
    if (next.length >= CIRCLE_COUNT) setDone(true)
    else setActiveIdx(activeIdx + 1)
  }

  async function handleNext() {
    setBusy(true); setErr('')
    const res = await api.mCalSave()
    setBusy(false)
    if (res?.success === false) { setErr(res.error || 'Something went wrong. Please try again.'); return }
    navigate('/assessment/phq9')
  }

  return (
    <AssessmentShell step="clicking" width="max-w-5xl" lost={lost}>
      <StepHeading kicker="Part 2 · Clicking warm-up" title="Click the circles in order">
        Click circle 1, then 2, and so on up to {CIRCLE_COUNT}. Move the mouse as you normally would.
      </StepHeading>

      <div ref={areaRef} className="relative h-[480px] rounded-3xl border border-border bg-white shadow-card overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(10,191,188,0.08),transparent_18rem),radial-gradient(circle_at_80%_70%,rgba(91,164,207,0.10),transparent_20rem)]" aria-hidden="true" />
        <div className="absolute left-0 right-0 top-4 z-10 flex justify-center" aria-live="polite">
          <span className="rounded-full bg-white border border-border px-4 py-1.5 text-sm font-semibold text-tmain shadow-card">
            {done ? 'All circles done' : `Click circle ${activeIdx + 1}`} · {clicked.length} of {CIRCLE_COUNT}
          </span>
        </div>

        {circles.map((c, i) => {
          const isClicked = clicked.includes(i)
          const isActive = i === activeIdx && !done
          const isPending = i > activeIdx
          return (
            <motion.button
              key={`${i}-${c.x}`}
              onClick={() => handleCircleClick(i)}
              disabled={isClicked || isPending || done}
              aria-label={isClicked ? `Circle ${i + 1}, done` : `Circle ${i + 1}`}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: isActive ? 1.15 : 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 320, damping: 20, delay: 0.04 * i }}
              className={`absolute flex h-16 w-16 select-none items-center justify-center rounded-full text-xl font-bold
                ${isClicked ? 'bg-success text-white' : isActive ? 'bg-accent-ink text-white cursor-pointer' : 'bg-[#DCEBEB] text-tsub'}`}
              style={{ left: c.x - 32, top: c.y - 32, boxShadow: isActive ? '0 0 0 12px rgba(10,191,188,0.18)' : 'none' }}
            >
              {isClicked ? <Check size={26} strokeWidth={3} aria-hidden="true" /> : i + 1}
            </motion.button>
          )
        })}

        <AnimatePresence>
          {done && (
            <motion.div className="absolute inset-0 flex items-center justify-center bg-white/70 backdrop-blur-[2px]"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <motion.div initial={{ scale: 0.9, y: 10 }} animate={{ scale: 1, y: 0 }} className="rounded-3xl bg-white p-8 text-center shadow-modal border border-border">
                <span className="mx-auto w-14 h-14 rounded-full bg-success text-white flex items-center justify-center"><Check size={28} strokeWidth={3} aria-hidden="true" /></span>
                <p className="mt-4 text-2xl font-bold text-tmain">Nicely done</p>
                <p className="text-tsub mt-1">Both warm-ups are finished.</p>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {err && <Alert tone="error" className="mt-4">{err}</Alert>}

      <div className="mt-8 flex flex-wrap justify-center gap-3">
        {!done && clicked.length > 0 && (
          <Button variant="secondary" size="lg" icon={RotateCcw} onClick={placeCircles}>Start over</Button>
        )}
        <Button size="lg" className="min-w-[260px]" iconRight={ArrowRight} disabled={!done} loading={busy} onClick={handleNext}>
          Continue
        </Button>
      </div>
    </AssessmentShell>
  )
}
