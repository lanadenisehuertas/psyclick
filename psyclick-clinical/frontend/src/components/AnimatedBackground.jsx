export default function AnimatedBackground({ variant = 'default' }) {
  const bubbles = variant === 'subtle'
    ? [
        { w: 480, h: 480, top: '-12%', left: '-6%',  bg: 'radial-gradient(circle, #0ABFBC, transparent)', anim: 'float1 14s ease-in-out infinite',       op: 0.10 },
        { w: 380, h: 380, top: '25%',  right: '-8%', bg: 'radial-gradient(circle, #5BA4CF, transparent)', anim: 'float2 17s ease-in-out infinite 2s',    op: 0.08 },
        { w: 300, h: 300, bottom: '5%',left: '18%',  bg: 'radial-gradient(circle, #36C98E, transparent)', anim: 'float3 20s ease-in-out infinite 4s',    op: 0.08 },
      ]
    : [
        { w: 560, h: 560, top: '-14%', left: '-7%',   bg: 'radial-gradient(circle, #0ABFBC, transparent)', anim: 'float1 13s ease-in-out infinite',       op: 0.18 },
        { w: 420, h: 420, top: '18%',  right: '-9%',  bg: 'radial-gradient(circle, #5BA4CF, transparent)', anim: 'float2 16s ease-in-out infinite 2.5s',  op: 0.14 },
        { w: 360, h: 360, bottom:'4%', left: '14%',   bg: 'radial-gradient(circle, #36C98E, transparent)', anim: 'float3 19s ease-in-out infinite 4.5s',  op: 0.13 },
        { w: 220, h: 220, top: '42%',  left: '42%',   bg: 'radial-gradient(circle, #0ABFBC, transparent)', anim: 'float1 11s ease-in-out infinite 6s',    op: 0.09 },
        { w: 260, h: 260, bottom:'22%',right: '18%',  bg: 'radial-gradient(circle, #F5A623, transparent)', anim: 'drift   22s ease-in-out infinite 1.5s', op: 0.08 },
      ]

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0" aria-hidden="true">
      {bubbles.map((b, i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            width: b.w,
            height: b.h,
            top: b.top,
            left: b.left,
            right: b.right,
            bottom: b.bottom,
            background: b.bg,
            opacity: b.op,
            filter: 'blur(60px)',
            animation: b.anim,
          }}
        />
      ))}
    </div>
  )
}
