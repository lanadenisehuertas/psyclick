import { motion, useReducedMotion } from 'motion/react'

// Node centres measured from images/LOGOggg.png (578 × 579). Signals travel
// from the hub out along the logo's own network lines.
const HUB = { x: 272, y: 220, r: 43 }
const NODES = [
  { x: 356, y: 145, r: 27 },
  { x: 390, y: 214, r: 28 },
  { x: 367, y: 315, r: 20 },
  { x: 297, y: 345, r: 33 },
  { x: 100, y: 245, r: 15 },
  { x: 204, y: 137, r: 29 },
  { x: 272, y: 135, r: 16 },
]
const CYCLE = 3.6

export default function AnimatedLogo({ size = 220 }) {
  const still = useReducedMotion()
  const loop = (extra = {}) => (still ? { duration: 0 } : { repeat: Infinity, ease: 'easeInOut', ...extra })

  return (
    <motion.div className="relative" style={{ width: size, height: size }} aria-hidden="true"
      animate={still ? undefined : { y: [0, -6, 0] }} transition={loop({ duration: 6 })}>

      {/* Soft glow in the logo colours */}
      <motion.div className="absolute -inset-[35%] rounded-full blur-2xl"
        style={{ background: 'radial-gradient(circle at 35% 40%, rgba(112,232,192,.55), transparent 55%), radial-gradient(circle at 70% 35%, rgba(104,216,232,.5), transparent 55%), radial-gradient(circle at 60% 75%, rgba(120,168,216,.55), transparent 60%)' }}
        animate={still ? undefined : { scale: [1, 1.08, 1], opacity: [0.75, 1, 0.75] }} transition={loop({ duration: 5 })} />

      {/* Orbit rings */}
      <svg className="absolute -inset-[16%] w-[132%] h-[132%]" viewBox="0 0 200 200">
        <defs>
          <linearGradient id="al-ring" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#70E8C0" />
            <stop offset=".5" stopColor="#68D8E8" />
            <stop offset="1" stopColor="#78A8D8" />
          </linearGradient>
        </defs>
        <motion.g style={{ originX: '100px', originY: '100px' }}
          animate={still ? undefined : { rotate: 360 }} transition={loop({ duration: 26, ease: 'linear' })}>
          <circle cx="100" cy="100" r="96" fill="none" stroke="url(#al-ring)" strokeWidth="1.6" strokeLinecap="round" strokeDasharray="150 60 40 60 90 200" />
          <circle cx="100" cy="4" r="3" fill="#70E8C0" />
          <circle cx="196" cy="100" r="2.2" fill="#78A8D8" />
        </motion.g>
        <motion.g style={{ originX: '100px', originY: '100px' }}
          animate={still ? undefined : { rotate: -360 }} transition={loop({ duration: 40, ease: 'linear' })}>
          <circle cx="100" cy="100" r="88" fill="none" stroke="#68D8E8" strokeOpacity=".45" strokeWidth="1" strokeDasharray="1 5" strokeLinecap="round" />
          <circle cx="12" cy="100" r="2.4" fill="#68D8E8" />
        </motion.g>
      </svg>

      {/* White plate so the logo's cut-out network reads as on paper */}
      <motion.div className="absolute inset-0 rounded-full bg-white"
        style={{ boxShadow: '0 0 0 6px rgba(255,255,255,.08), 0 24px 60px -12px rgba(0,0,0,.45), inset 0 -6px 18px rgba(104,216,232,.18)' }}
        initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: 'spring', stiffness: 140, damping: 16 }} />

      <motion.div className="absolute inset-[7%]"
        initial={{ scale: 0.7, opacity: 0, rotate: -30 }} animate={{ scale: 1, opacity: 1, rotate: 0 }}
        transition={{ type: 'spring', stiffness: 110, damping: 14, delay: 0.1 }}>
        <img src={`${import.meta.env.BASE_URL}images/LOGOggg.png`} alt="" className="w-full h-full object-contain" />

        {/* Signals moving through the network */}
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 578 579">
          {!still && NODES.map((n, i) => {
            const delay = 0.9 + i * (CYCLE / NODES.length)
            return (
              <g key={i}>
                <motion.circle r="9" fill="#3D5FA8"
                  initial={{ cx: HUB.x, cy: HUB.y, opacity: 0 }}
                  animate={{ cx: [HUB.x, n.x], cy: [HUB.y, n.y], opacity: [0, 1, 0] }}
                  transition={{ duration: 1.1, delay, repeat: Infinity, repeatDelay: CYCLE - 1.1, ease: 'easeIn' }} />
                <motion.circle cx={n.x} cy={n.y} fill="none" stroke="#fff" strokeWidth="5"
                  initial={{ r: n.r, opacity: 0 }}
                  animate={{ r: [n.r, n.r + 26], opacity: [0.9, 0] }}
                  transition={{ duration: 0.9, delay: delay + 1.05, repeat: Infinity, repeatDelay: CYCLE - 0.9, ease: 'easeOut' }} />
              </g>
            )
          })}
          {!still && (
            <motion.circle cx={HUB.x} cy={HUB.y} fill="none" stroke="#fff" strokeWidth="6"
              initial={{ r: HUB.r, opacity: 0 }}
              animate={{ r: [HUB.r, HUB.r + 34], opacity: [0.9, 0] }}
              transition={{ duration: 1.4, delay: 0.6, repeat: Infinity, repeatDelay: CYCLE - 1.4, ease: 'easeOut' }} />
          )}
        </svg>
      </motion.div>
    </motion.div>
  )
}
