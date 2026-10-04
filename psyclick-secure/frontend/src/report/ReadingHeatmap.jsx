import { useMemo, useState } from 'react'
import { motion } from 'motion/react'
import { MousePointer2 } from 'lucide-react'
import { DOMAIN_NAMES, LEVEL_NAMES } from './text.js'

// Heat scale drawn from the PsyClick logo: mint → cyan → periwinkle → deep blue
const STOPS = [
  [0.00, [255, 255, 255]],
  [0.15, [112, 232, 192]],   // mint   #70E8C0
  [0.45, [104, 216, 232]],   // cyan   #68D8E8
  [0.75, [120, 168, 216]],   // peri   #78A8D8
  [1.00, [61, 95, 168]],     // deep   #3D5FA8
]
function heat(t) {
  if (t <= 0) return null
  for (let i = 1; i < STOPS.length; i++) {
    const [p1, c1] = STOPS[i - 1], [p2, c2] = STOPS[i]
    if (t <= p2) {
      const k = (t - p1) / (p2 - p1)
      return c1.map((v, j) => Math.round(v + (c2[j] - v) * k))
    }
  }
  return STOPS[STOPS.length - 1][1]
}
const STOP_WORDS = new Set('a an the to of in on at for and or but is are was were be been do does did you your yours i me my it its this that with when what how which who about from as by if so than then there they them their have has had not no'.split(' '))
const clean = w => w.toLowerCase().replace(/[^a-z'’-]/g, '')

export default function ReadingHeatmap({ snapshots }) {
  const [focus, setFocus] = useState(null)   // {item, word, ms, n}
  const rows = useMemo(() => (snapshots || []).map(s => {
    const by = {}
    ;(s.hover_words || []).forEach(h => { by[h.word] = h })
    const total = (s.hover_words || []).reduce((a, h) => a + (h.dwell_ms || 0), 0)
    return { s, words: (s.prompt || '').split(' '), by, total }
  }), [snapshots])

  const maxMs = Math.max(1, ...rows.flatMap(r => Object.values(r.by).map(h => h.dwell_ms || 0)))
  const top = useMemo(() => {
    const agg = {}
    rows.forEach(r => Object.values(r.by).forEach(h => {
      const k = clean(h.word)
      if (!k || STOP_WORDS.has(k)) return
      const a = agg[k] || (agg[k] = { word: k, ms: 0, items: new Set() })
      a.ms += h.dwell_ms || 0
      a.items.add(r.s.item_id)
    }))
    return Object.values(agg).sort((a, b) => b.ms - a.ms).slice(0, 6)
  }, [rows])
  const anyHover = rows.some(r => r.total > 0)

  if (!rows.length) return null

  return (
    <div>
      {anyHover ? (
        <div className="rounded-xl bg-[#F4FAFB] border border-[#D9E6EA] p-4">
          <p className="text-sm font-semibold text-[#0F2A33]">Words that held attention</p>
          <p className="text-xs text-[#4A6670]">Common words like “the” and “you” are left out of this list.</p>
          <ol className="mt-3 grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {top.map((t, i) => {
              const [r, g, b] = heat(Math.min(1, t.ms / Math.max(...top.map(x => x.ms)))) || [255, 255, 255]
              return (
                <motion.li key={t.word} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 * i }}
                  className="flex items-center gap-3 rounded-lg bg-white border border-[#D9E6EA] px-3 py-2">
                  <span className="font-mono text-xs text-[#4A6670] w-4">{i + 1}</span>
                  <span className="font-semibold text-[#0F2A33] flex-1 truncate">“{t.word}”</span>
                  <span className="font-mono text-sm text-[#0F2A33]">{(t.ms / 1000).toFixed(1)} s</span>
                  <span className="w-12 h-2 rounded-full bg-[#E3EDF0] overflow-hidden" aria-hidden="true">
                    <span className="block h-full rounded-full" style={{ width: `${(t.ms / top[0].ms) * 100}%`, background: `rgb(${r},${g},${b})` }} />
                  </span>
                </motion.li>
              )
            })}
          </ol>
        </div>
      ) : (
        <div className="rounded-xl bg-[#F4FAFB] border border-[#D9E6EA] p-4 flex gap-3 items-start">
          <MousePointer2 size={18} className="text-[#3D5FA8] mt-0.5 flex-shrink-0" aria-hidden="true" />
          <p className="text-sm text-[#0F2A33]">
            The cursor didn't rest on the prompt words this time. Many people read without moving the mouse, so use the
            pause before typing (in the session trace) as the reading signal instead.
          </p>
        </div>
      )}

      <ul className="mt-4 divide-y divide-[#E3EDF0]">
        {rows.map(({ s, words, by, total }) => (
          <li key={s.item_id} className="py-3 grid grid-cols-[130px_1fr_96px] gap-4 items-start">
            <div>
              <p className="font-mono text-sm font-semibold text-[#0F2A33]">{s.item_id}</p>
              <p className="text-xs text-[#4A6670]">{LEVEL_NAMES[s.level]} · {DOMAIN_NAMES[s.group_id]}</p>
            </div>
            <p className="text-[15px] leading-[2] text-[#0F2A33]">
              {words.map((w, i) => {
                const h = by[w]
                const t = h ? Math.min(1, (h.dwell_ms || 0) / maxMs) : 0
                const c = heat(t)
                const dark = t > 0.8
                return (<span key={i}>
                  <span
                    tabIndex={h ? 0 : -1}
                    onMouseEnter={() => h && setFocus({ item: s.item_id, word: w, ms: h.dwell_ms, n: h.hover_count })}
                    onMouseLeave={() => setFocus(null)}
                    onFocus={() => h && setFocus({ item: s.item_id, word: w, ms: h.dwell_ms, n: h.hover_count })}
                    onBlur={() => setFocus(null)}
                    aria-label={h ? `${w}: lingered ${(h.dwell_ms / 1000).toFixed(1)} seconds` : undefined}
                    className={`rounded px-0.5 -mx-0.5 py-0.5 transition-shadow ${h ? 'cursor-help outline-none focus-visible:ring-2 focus-visible:ring-[#0A6B80]' : ''}
                      ${focus?.item === s.item_id && focus?.word === w ? 'ring-2 ring-[#0F2A33]' : ''}`}
                    style={c ? { background: `rgb(${c[0]},${c[1]},${c[2]})`, color: dark ? '#fff' : '#0F2A33', fontWeight: t > 0.3 ? 600 : 400 } : undefined}>
                    {w}
                  </span>{' '}</span>
                )
              })}
              {focus?.item === s.item_id && (
                <span className="ml-2 inline-flex items-center rounded-md bg-[#0F2A33] text-white text-xs px-2 py-1 align-middle" role="status">
                  lingered {(focus.ms / 1000).toFixed(1)} s · {focus.n} stop{focus.n !== 1 ? 's' : ''}
                </span>
              )}
            </p>
            <div className="text-right">
              <p className="font-mono text-sm text-[#0F2A33]">{((s.pre_typing_pause_ms || 0) / 1000).toFixed(1)} s</p>
              <p className="text-xs text-[#4A6670]">before typing</p>
              {total > 0 && <p className="text-xs text-[#4A6670] mt-0.5">{(total / 1000).toFixed(1)} s on words</p>}
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-[#4A6670]">
        <span>Less time</span>
        <span className="h-2.5 w-40 rounded-full" style={{ background: 'linear-gradient(90deg,#fff,#70E8C0 15%,#68D8E8 45%,#78A8D8 75%,#3D5FA8)', border: '1px solid #D9E6EA' }} aria-hidden="true" />
        <span>More time the cursor rested on the word</span>
      </div>
    </div>
  )
}
