import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'motion/react'
import { DOMAIN_NAMES, DOMAIN_TIPS, LEVEL_NAMES, HEALTHY_GAP, MCID, phqLabel, gadLabel } from './text.js'

// ── palette (shared with print) ──────────────────────────────────────────────
export const C = {
  ink: '#14211F', sub: '#4E6662', grid: '#E2EAE7', gridMajor: '#CFDCD7', paper: '#FBFCFB',
  band: '#CFE8DF', teal: '#0C7C78', amber: '#B7791F', coral: '#B83A38', muted: '#A9BAB6',
}
const FONT_MONO = "'IBM Plex Mono', ui-monospace, monospace"

function useWidth() {
  const ref = useRef(null)
  const [w, setW] = useState(0)
  useLayoutEffect(() => {
    if (!ref.current) return
    const el = ref.current
    setW(el.clientWidth)
    const ro = new ResizeObserver(([e]) => setW(Math.round(e.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, w]
}

function niceMax(v) {
  const p = Math.pow(10, Math.floor(Math.log10(Math.max(v, 1))))
  const steps = [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]
  return steps.find(st => st * p >= v) * p
}

// Chart-paper grid, the instrument motif — only ever drawn behind real data.
function ChartPaper({ x, y, w, h, id }) {
  return (
    <g aria-hidden="true">
      <defs>
        <pattern id={`${id}-minor`} width="10" height="10" patternUnits="userSpaceOnUse">
          <path d="M10 0H0V10" fill="none" stroke={C.grid} strokeWidth="0.6" />
        </pattern>
        <pattern id={`${id}-major`} width="50" height="50" patternUnits="userSpaceOnUse">
          <rect width="50" height="50" fill={`url(#${id}-minor)`} />
          <path d="M50 0H0V50" fill="none" stroke={C.gridMajor} strokeWidth="0.9" />
        </pattern>
      </defs>
      <rect x={x} y={y} width={w} height={h} fill={C.paper} />
      <rect x={x} y={y} width={w} height={h} fill={`url(#${id}-major)`} />
    </g>
  )
}

// ── 1. Session trace ─────────────────────────────────────────────────────────
export function SessionTrace({ snapshots, itemP95, itemP99 }) {
  const [ref, width] = useWidth()
  const [hover, setHover] = useState(null)
  const snaps = snapshots || []
  const W = Math.max(width, 320)
  const M = { l: 52, r: 18, t: 34, b: 0 }
  const plotH = 220, gap = 62, pauseH = 64, labelH = 34
  const H = M.t + plotH + labelH + gap + pauseH + 22
  const pw = W - M.l - M.r
  const n = snaps.length || 1
  const step = pw / n
  const xAt = i => M.l + step * (i + 0.5)

  const vals = snaps.map(s => s.flag === 'NO_DATA' ? null : Number(s.t2_score || 0))
  const yMax = niceMax(Math.max(itemP99 * 1.1, ...vals.filter(v => v != null).map(v => v * 1.08), 1))
  const yAt = v => M.t + plotH - (Math.min(v, yMax) / yMax) * plotH
  const ticks = [0, yMax / 4, yMax / 2, (3 * yMax) / 4, yMax]

  const pauses = snaps.map(s => (s.pre_typing_pause_ms || 0) / 1000)
  const pMax = Math.max(10, ...pauses)
  const pTop = M.t + plotH + labelH + gap
  const pAt = v => pTop + pauseH - (v / pMax) * pauseH

  // line segments break at prompts with no typing
  const segments = []
  let cur = []
  vals.forEach((v, i) => { if (v == null) { if (cur.length) segments.push(cur); cur = [] } else cur.push([xAt(i), yAt(v)]) })
  if (cur.length) segments.push(cur)
  const pathOf = pts => pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ')

  // topic spans across consecutive prompts
  const spans = []
  snaps.forEach((s, i) => {
    const last = spans[spans.length - 1]
    if (last && last.gid === s.group_id) last.end = i
    else spans.push({ gid: s.group_id, start: i, end: i })
  })

  const h = hover != null ? snaps[hover] : null
  const dotFill = v => v > itemP99 ? C.coral : v > itemP95 ? C.amber : C.teal

  return (
    <div ref={ref} className="relative">
      {width > 0 && (
        <svg width={W} height={H} role="img" aria-label={`Session trace across ${snaps.length} prompts`} style={{ display: 'block' }}>
          <ChartPaper x={M.l} y={M.t} w={pw} h={plotH} id="trace" />
          {/* healthy band */}
          <rect x={M.l} y={yAt(itemP95)} width={pw} height={yAt(0) - yAt(itemP95)} fill={C.band} opacity="0.7" />
          <text x={M.l + 8} y={yAt(0) - 8} fontSize="11" fill={C.teal} fontWeight="600">Healthy range</text>
          <line x1={M.l} x2={M.l + pw} y1={yAt(itemP99)} y2={yAt(itemP99)} stroke={C.coral} strokeDasharray="5 4" strokeWidth="1.2" />
          <text x={M.l + pw - 6} y={yAt(itemP99) - 6} fontSize="11" fill={C.coral} textAnchor="end">Higher than 99% of healthy adults</text>

          {/* y axis */}
          {ticks.map(t => (
            <g key={t}>
              <text x={M.l - 8} y={yAt(t) + 4} fontSize="11" fill={C.sub} textAnchor="end" fontFamily={FONT_MONO}>{Math.round(t)}</text>
            </g>
          ))}
          <text x={14} y={M.t + plotH / 2} fontSize="11" fill={C.sub} transform={`rotate(-90 14 ${M.t + plotH / 2})`} textAnchor="middle">Change</text>

          {/* topic spans */}
          {spans.map((sp, k) => {
            const x1 = M.l + step * sp.start, x2 = M.l + step * (sp.end + 1)
            return (
              <g key={k}>
                {k > 0 && <line x1={x1} x2={x1} y1={M.t - 22} y2={M.t + plotH} stroke={C.gridMajor} strokeWidth="1" />}
                <text x={(x1 + x2) / 2} y={M.t - 12} fontSize="12" fill={C.ink} fontWeight="600" textAnchor="middle">{DOMAIN_NAMES[sp.gid] || `Topic ${sp.gid}`}</text>
              </g>
            )
          })}

          {/* trace */}
          {segments.map((pts, k) => (
            <motion.path key={k} d={pathOf(pts)} fill="none" stroke={C.ink} strokeWidth="2" strokeLinejoin="round"
              initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }} />
          ))}
          {snaps.map((s, i) => {
            const v = vals[i]
            const active = hover === i
            return v == null ? (
              <circle key={i} cx={xAt(i)} cy={yAt(0) - 10} r="5" fill="#fff" stroke={C.muted} strokeWidth="1.5" strokeDasharray="2 2" />
            ) : (
              <circle key={i} cx={xAt(i)} cy={yAt(v)} r={active ? 8 : 6} fill={dotFill(v)} stroke="#fff" strokeWidth="2" />
            )
          })}

          {/* x labels */}
          {snaps.map((s, i) => (
            <g key={i}>
              <text x={xAt(i)} y={M.t + plotH + 16} fontSize="11" fill={C.ink} textAnchor="middle" fontFamily={FONT_MONO} fontWeight="600">{s.item_id}</text>
              <text x={xAt(i)} y={M.t + plotH + 29} fontSize="10" fill={C.sub} textAnchor="middle">{LEVEL_NAMES[s.level] || s.level}</text>
            </g>
          ))}

          {/* pause strip */}
          <text x={M.l} y={pTop - 30} fontSize="12" fill={C.ink} fontWeight="600">Pause before typing</text>
          <text x={M.l + 132} y={pTop - 30} fontSize="11" fill={C.sub}>seconds from seeing the prompt to the first key</text>
          <line x1={M.l} x2={M.l + pw} y1={pTop + pauseH} y2={pTop + pauseH} stroke={C.gridMajor} />
          {pauses.map((p, i) => (
            <g key={i}>
              <line x1={xAt(i)} x2={xAt(i)} y1={pTop + pauseH} y2={pAt(p)} stroke={C.sub} strokeWidth="2" />
              <circle cx={xAt(i)} cy={pAt(p)} r="3.5" fill={C.ink} />
              <text x={xAt(i)} y={pAt(p) - 7} fontSize="10" fill={C.sub} textAnchor="middle" fontFamily={FONT_MONO}>{p.toFixed(1)}</text>
            </g>
          ))}

          {/* hit areas */}
          {snaps.map((s, i) => (
            <rect key={i} x={M.l + step * i} y={M.t} width={step} height={H - M.t - 4} fill="transparent"
              tabIndex={0} role="button"
              aria-label={`Prompt ${s.item_id}: change ${vals[i] == null ? 'not scored' : vals[i].toFixed(0)}, pause ${pauses[i].toFixed(1)} seconds`}
              onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(i)} onBlur={() => setHover(null)} style={{ outline: 'none', cursor: 'default' }} />
          ))}
          {hover != null && <rect x={M.l + step * hover} y={M.t} width={step} height={plotH} fill={C.ink} opacity="0.04" pointerEvents="none" />}
        </svg>
      )}

      {h && (
        <div className="pointer-events-none absolute z-20 w-[290px] rounded-xl bg-[#14211F] text-white p-4 shadow-xl text-sm"
          style={{ left: Math.min(Math.max(xAt(hover) - 145, 0), W - 290), top: M.t + plotH + 44 }}>
          <p className="font-mono text-xs text-white/60">{h.item_id} · {DOMAIN_NAMES[h.group_id]} · {LEVEL_NAMES[h.level]} prompt</p>
          {h.prompt && <p className="mt-1.5 leading-snug">“{h.prompt}”</p>}
          <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            <dt className="text-white/60">Change</dt><dd className="font-mono text-right">{h.flag === 'NO_DATA' ? 'not scored' : Number(h.t2_score).toFixed(0)}</dd>
            <dt className="text-white/60">Pause before typing</dt><dd className="font-mono text-right">{((h.pre_typing_pause_ms || 0) / 1000).toFixed(1)} s</dd>
            <dt className="text-white/60">Answer length</dt><dd className="font-mono text-right">{h.response_len ?? '—'} chars</dd>
            {h.hover_words?.[0] && (<><dt className="text-white/60">Word read longest</dt><dd className="text-right">“{h.hover_words[0].word}”</dd></>)}
          </dl>
        </div>
      )}
    </div>
  )
}

// ── 2. Topic × strength map ──────────────────────────────────────────────────
function mix(a, b, t) {
  const pa = a.match(/\w\w/g).map(x => parseInt(x, 16)), pb = b.match(/\w\w/g).map(x => parseInt(x, 16))
  return '#' + pa.map((v, i) => Math.round(v + (pb[i] - v) * t).toString(16).padStart(2, '0')).join('')
}

export function TopicGrid({ snapshots, itemP95 }) {
  const [mode, setMode] = useState('change')
  const cells = useMemo(() => {
    const m = {}
    ;(snapshots || []).forEach(s => {
      const key = `${s.group_id}-${s.level}`
      const c = m[key] || (m[key] = { change: [], pause: [] })
      if (s.flag !== 'NO_DATA') c.change.push(Number(s.t2_score || 0))
      c.pause.push((s.pre_typing_pause_ms || 0) / 1000)
    })
    return m
  }, [snapshots])
  const avg = a => a.length ? a.reduce((x, y) => x + y, 0) / a.length : null
  const pauseMax = Math.max(10, ...Object.values(cells).map(c => avg(c.pause) || 0))

  function cellStyle(v) {
    if (v == null) return { background: 'transparent', color: C.muted }
    let bg
    if (mode === 'change') bg = v > itemP95 ? mix('F6D9D6', 'B83A38', Math.min(1, (v - itemP95) / itemP95)) : mix('F1F7F5', '0C7C78', Math.min(1, v / itemP95) * 0.85)
    else bg = mix('F1F7F5', '14211F', Math.min(1, v / pauseMax) * 0.85)
    const dark = parseInt(bg.slice(1, 3), 16) * 0.3 + parseInt(bg.slice(3, 5), 16) * 0.59 + parseInt(bg.slice(5, 7), 16) * 0.11 < 140
    return { background: bg, color: dark ? '#fff' : C.ink }
  }

  return (
    <div>
      <div className="flex items-center justify-end mb-3">
        <div role="tablist" aria-label="Map shows" className="inline-flex rounded-lg border border-[#D6E0DC] p-0.5 bg-white text-sm">
          {[['change', 'Change'], ['pause', 'Pause before typing']].map(([k, l]) => (
            <button key={k} role="tab" aria-selected={mode === k} onClick={() => setMode(k)}
              className={`px-3 h-8 rounded-md font-semibold cursor-pointer transition-colors ${mode === k ? 'bg-[#14211F] text-white' : 'text-[#4E6662] hover:text-[#14211F]'}`}>{l}</button>
          ))}
        </div>
      </div>
      <table className="w-full border-separate" style={{ borderSpacing: 6 }}>
        <thead>
          <tr>
            <th className="text-left text-xs font-semibold text-[#4E6662] font-normal pb-1 w-[34%]"><span className="sr-only">Topic</span></th>
            {['A', 'B', 'C'].map(l => <th key={l} scope="col" className="text-sm font-semibold text-[#14211F] pb-1">{LEVEL_NAMES[l]}<span className="block text-xs font-normal text-[#4E6662]">prompts</span></th>)}
          </tr>
        </thead>
        <tbody>
          {[1, 2, 3, 4].map(g => (
            <tr key={g}>
              <th scope="row" className="text-left align-middle pr-2">
                <span className="block text-sm font-semibold text-[#14211F]">{DOMAIN_NAMES[g]}</span>
                <span className="block text-xs text-[#4E6662] font-normal">{DOMAIN_TIPS[g]}</span>
              </th>
              {['A', 'B', 'C'].map(l => {
                const c = cells[`${g}-${l}`]
                const v = c ? avg(mode === 'change' ? c.change : c.pause) : null
                const st = cellStyle(c ? v : null)
                return (
                  <td key={l} className="h-[60px] rounded-lg text-center align-middle font-mono text-[15px] font-semibold transition-colors"
                    style={{ ...st, border: c ? 'none' : `1px dashed ${C.gridMajor}` }}>
                    {!c ? <span className="text-xs font-sans font-normal">no prompt</span>
                      : v == null ? <span className="text-xs font-sans font-normal">not scored</span>
                      : mode === 'change' ? Math.round(v) : `${v.toFixed(1)} s`}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-[#4E6662]">
        {mode === 'change' ? (<>
          <span className="inline-flex items-center gap-1.5"><span className="w-8 h-2.5 rounded-sm" style={{ background: 'linear-gradient(90deg,#F1F7F5,#0C7C78)' }} />within healthy range</span>
          <span className="inline-flex items-center gap-1.5"><span className="w-8 h-2.5 rounded-sm" style={{ background: 'linear-gradient(90deg,#F6D9D6,#B83A38)' }} />above healthy range (&gt; {Math.round(itemP95)})</span>
        </>) : (
          <span className="inline-flex items-center gap-1.5"><span className="w-8 h-2.5 rounded-sm" style={{ background: 'linear-gradient(90deg,#F1F7F5,#14211F)' }} />longer pause = darker</span>
        )}
      </div>
    </div>
  )
}

// ── 3. Typing rhythm ─────────────────────────────────────────────────────────
export function RhythmChart({ flights }) {
  const [ref, width] = useWidth()
  const gaps = (flights || []).filter(f => f > 0)
  const BIN = 0.05, MAXB = 20                           // 0–1 s in 50 ms bins + overflow
  const bins = Array(MAXB + 1).fill(0)
  gaps.forEach(g => { bins[Math.min(MAXB, Math.floor(g / BIN))] += 1 })
  const sorted = [...gaps].sort((a, b) => a - b)
  const median = sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0
  const long = gaps.filter(g => g > 1).length

  const W = Math.max(width, 300), H = 190, M = { l: 40, r: 12, t: 14, b: 30 }
  const pw = W - M.l - M.r, ph = H - M.t - M.b
  const bw = pw / bins.length
  const yMax = Math.max(...bins, 1)
  const xAtSec = s => M.l + Math.min(s / BIN, MAXB) * bw

  return (
    <div>
      <dl className="grid grid-cols-3 gap-4 mb-4">
        {[
          ['Typical gap', `${(median * 1000).toFixed(0)} ms`, 'median between key presses'],
          ['Pauses over 1 s', `${long}`, gaps.length ? `${((long / gaps.length) * 100).toFixed(1)}% of gaps` : '—'],
          ['Key presses', `${gaps.length}`, 'in the written answers'],
        ].map(([k, v, d]) => (
          <div key={k}>
            <dt className="text-xs text-[#4E6662]">{k}</dt>
            <dd className="font-mono text-2xl font-semibold text-[#14211F] leading-tight">{v}</dd>
            <dd className="text-xs text-[#4E6662]">{d}</dd>
          </div>
        ))}
      </dl>
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-[#4E6662] mb-2" aria-hidden="true">
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm" style={{ background: C.band }} />healthy adults' average gap</span>
        <span className="inline-flex items-center gap-1.5"><span className="w-3 border-t-2 border-dashed" style={{ borderColor: C.coral }} />this client's typical gap</span>
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm" style={{ background: C.amber }} />pauses over 1 second</span>
      </div>
      <div ref={ref}>
        {width > 0 && gaps.length > 0 && (
          <svg width={W} height={H} role="img" aria-label={`Typing rhythm: median gap ${(median * 1000).toFixed(0)} ms, ${long} pauses over one second`}>
            <ChartPaper x={M.l} y={M.t} w={pw} h={ph} id="rhythm" />
            <rect x={xAtSec(HEALTHY_GAP.p25)} y={M.t} width={xAtSec(HEALTHY_GAP.p75) - xAtSec(HEALTHY_GAP.p25)} height={ph} fill={C.band} opacity="0.75" />
            {bins.map((c, i) => {
              const h = (c / yMax) * ph
              return <rect key={i} x={M.l + i * bw + 1.5} y={M.t + ph - h} width={Math.max(bw - 3, 1)} height={h} rx="2"
                fill={i === MAXB ? C.amber : '#3E5753'} opacity={i === MAXB ? 0.9 : 0.85} />
            })}
            <line x1={xAtSec(median)} x2={xAtSec(median)} y1={M.t} y2={M.t + ph} stroke={C.coral} strokeWidth="1.5" strokeDasharray="4 3" />
            {[0, 0.25, 0.5, 0.75].map(s => (
              <text key={s} x={xAtSec(s)} y={H - 10} fontSize="11" fill={C.sub} textAnchor="middle" fontFamily={FONT_MONO}>{s * 1000} ms</text>
            ))}
            <text x={M.l + MAXB * bw + bw / 2} y={H - 10} fontSize="11" fill={C.amber} textAnchor="middle" fontFamily={FONT_MONO}>1 s+</text>
          </svg>
        )}
        {gaps.length === 0 && <p className="text-sm text-[#4E6662]">No typing was captured in the written answers.</p>}
      </div>
    </div>
  )
}

// ── 4. Change since earlier sessions ─────────────────────────────────────────
function Spark({ values, current, band, w = 160, h = 40 }) {
  const pts = values.map((v, i) => [values.length === 1 ? w / 2 : 6 + (i * (w - 12)) / (values.length - 1), v])
  const max = Math.max(band || 0, ...values, 1) * 1.1
  const y = v => h - 4 - (v / max) * (h - 8)
  return (
    <svg width={w} height={h} aria-hidden="true">
      {band != null && <rect x="0" y={y(band)} width={w} height={h - 4 - y(band)} fill={C.band} opacity="0.7" />}
      <path d={pts.map((p, i) => `${i ? 'L' : 'M'}${p[0]} ${y(p[1])}`).join(' ')} fill="none" stroke={C.sub} strokeWidth="1.5" />
      {pts.map((p, i) => <circle key={i} cx={p[0]} cy={y(p[1])} r={i === current ? 4.5 : 2.5} fill={i === current ? C.ink : C.sub} />)}
    </svg>
  )
}

export function ChangeSince({ sessions, sessionId, sessionP95 }) {
  if (!sessions) return <p className="text-sm text-[#4E6662]">Loading earlier sessions…</p>
  const ordered = [...sessions].sort((a, b) => a.session_id - b.session_id)
  const idx = ordered.findIndex(s => String(s.session_id) === String(sessionId))
  if (idx <= 0) {
    return (
      <p className="text-[15px] text-[#14211F]">
        This is the client's first session. It becomes their personal baseline: from the next visit,
        this section shows how their answers and behaviour have moved since today.
      </p>
    )
  }
  const now = ordered[idx], prev = ordered[idx - 1], first = ordered[0]
  const history = ordered.slice(0, idx + 1)

  const rows = [
    { key: 'phq', name: 'Depression (PHQ-9)', fmt: v => v, label: phqLabel, mcid: MCID.phq },
    { key: 'gad', name: 'Anxiety (GAD-7)', fmt: v => v, label: gadLabel, mcid: MCID.gad },
    { key: 't2', name: 'Behaviour change', fmt: v => Math.round(v), band: sessionP95,
      label: v => v <= sessionP95 ? 'within healthy range' : 'above healthy range' },
  ]

  return (
    <div>
      <p className="text-sm text-[#4E6662] mb-4">
        Compared with the previous session ({new Date(String(prev.timestamp).replace(' ', 'T') + 'Z').toLocaleDateString(undefined, { dateStyle: 'medium' })})
        {idx > 1 ? ` and with the first (${new Date(String(first.timestamp).replace(' ', 'T') + 'Z').toLocaleDateString(undefined, { dateStyle: 'medium' })})` : ''}.
      </p>
      <div className="divide-y divide-[#E2EAE7]">
        {rows.map(r => {
          const d = Number(now[r.key] || 0) - Number(prev[r.key] || 0)
          const meaningful = r.mcid ? Math.abs(d) >= r.mcid : (Number(prev[r.key]) <= sessionP95) !== (Number(now[r.key]) <= sessionP95)
          const worse = d > 0
          return (
            <div key={r.key} className="py-3 grid grid-cols-[1.3fr_1fr_1.4fr_auto] gap-4 items-center">
              <div>
                <p className="font-semibold text-[#14211F]">{r.name}</p>
                <p className="text-xs text-[#4E6662]">{r.label(Number(now[r.key] || 0))}</p>
              </div>
              <p className="font-mono text-[#14211F]">
                <span className="text-[#4E6662]">{r.fmt(Number(prev[r.key] || 0))}</span> → <span className="font-semibold">{r.fmt(Number(now[r.key] || 0))}</span>
              </p>
              <p className={`text-sm font-semibold ${!meaningful ? 'text-[#4E6662]' : worse ? 'text-coral-ink' : 'text-success-ink'}`}>
                {!meaningful ? (r.mcid ? `No meaningful change (needs ±${r.mcid})` : 'Same side of the healthy limit')
                  : r.mcid ? (worse ? `Worse by ${d} — meaningful` : `Better by ${-d} — meaningful`)
                  : (worse ? 'Moved above the healthy range' : 'Returned to the healthy range')}
              </p>
              <Spark values={history.map(s => Number(s[r.key] || 0))} current={history.length - 1} band={r.band} />
            </div>
          )
        })}
      </div>
      <p className="mt-3 text-xs text-[#4E6662]">
        Questionnaire changes count as meaningful at 5 points for PHQ-9 and 4 for GAD-7. Behaviour is re-measured against a new
        warm-up each visit, so compare it by whether it sits inside the healthy range rather than by its exact size.
      </p>
    </div>
  )
}
