import { useRef, useState } from 'react'
import { Info } from 'lucide-react'
import { GLOSSARY } from './text.js'

// Small "what is this?" explainer. Opens on hover and on keyboard focus.
export default function InfoTooltip({ glossaryKey }) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const ref = useRef(null)
  const entry = GLOSSARY[glossaryKey]
  if (!entry) return null

  function show() {
    const r = ref.current?.getBoundingClientRect()
    if (r) setPos({ x: Math.min(r.left, window.innerWidth - 340), y: r.bottom + 8 })
    setOpen(true)
  }

  return (
    <span className="relative inline-flex align-middle" data-print-hide>
      <button ref={ref} type="button" aria-label={`What is ${entry.title}?`}
        onMouseEnter={show} onMouseLeave={() => setOpen(false)} onFocus={show} onBlur={() => setOpen(false)}
        className="ml-1.5 w-6 h-6 rounded-full inline-flex items-center justify-center text-[#4A6670] hover:text-[#0F2A33] hover:bg-black/[0.05] cursor-help focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#0A6B80]">
        <Info size={15} aria-hidden="true" />
      </button>
      {open && (
        <span role="tooltip" className="fixed z-[9999] w-[320px] rounded-xl bg-[#0F2A33] text-white shadow-xl p-4 text-left"
          style={{ left: pos.x, top: pos.y }}>
          <span className="block font-display font-semibold text-[15px]">{entry.title}</span>
          <span className="block text-[13px] text-white/90 mt-1.5 leading-snug">{entry.what}</span>
          <span className="block text-[13px] text-[#9FE8D4] mt-2 leading-snug">{entry.flag}</span>
          <span className="block text-[12px] text-white/55 mt-2 leading-snug font-mono">{entry.how}</span>
        </span>
      )}
    </span>
  )
}
