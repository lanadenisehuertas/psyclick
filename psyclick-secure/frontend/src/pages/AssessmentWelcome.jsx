import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { Keyboard, MousePointerClick, ListChecks, PenLine, ArrowRight, Coffee, Smile, Clock } from 'lucide-react'
import AssessmentShell, { StepHeading } from '../components/AssessmentShell.jsx'
import { useApp } from '../context/AppContext.jsx'
import { Button, EASE } from '../components/ui.jsx'

const PARTS = [
  { icon: Keyboard,          tone: 'teal',  title: 'Type a short paragraph', text: 'A quick warm-up so we learn your normal typing.' },
  { icon: MousePointerClick, tone: 'blue',  title: 'Click five circles', text: 'Another warm-up, this time with the mouse.' },
  { icon: ListChecks,        tone: 'green', title: 'Answer 16 short questions', text: 'Choose how often something has bothered you.' },
  { icon: PenLine,           tone: 'amber', title: 'Write 12 short answers', text: 'A sentence or two about everyday situations.' },
]

const TIPS = [
  { icon: Smile, text: 'There are no right or wrong answers.' },
  { icon: Clock, text: 'Go at your usual pace — it is not a race.' },
  { icon: Coffee, text: 'Need a break? Just tell your clinician.' },
]

export default function AssessmentWelcome() {
  const navigate = useNavigate()
  const { client } = useApp()
  return (
    <AssessmentShell width="max-w-4xl" lost={!client}>
      <StepHeading kicker="Welcome" title="Thank you for taking part">
        This takes about 15 minutes. Here is what you will do.
      </StepHeading>

      <ol className="grid sm:grid-cols-2 gap-4">
        {PARTS.map((p, i) => (
          <motion.li key={p.title} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.08 * i, ease: EASE }}
            className="bg-white rounded-2xl border border-border p-5 flex gap-4">
            <span className="font-mono text-[28px] leading-none font-semibold text-accent-ink w-9 flex-shrink-0" aria-hidden="true">{i + 1}</span>
            <div>
              <p className="text-sm text-tsub flex items-center gap-1.5"><p.icon size={15} aria-hidden="true" /> Part {i + 1}</p>
              <p className="font-display text-lg font-semibold text-tmain leading-snug">{p.title}</p>
              <p className="text-tsub mt-0.5">{p.text}</p>
            </div>
          </motion.li>
        ))}
      </ol>

      <ul className="mt-6 grid sm:grid-cols-3 gap-3">
        {TIPS.map(t => (
          <li key={t.text} className="flex items-center gap-3 rounded-xl bg-white/70 border border-border px-4 py-3 text-tmain">
            <t.icon size={20} className="text-accent-ink flex-shrink-0" aria-hidden="true" />{t.text}
          </li>
        ))}
      </ul>

      <div className="mt-10 flex justify-center">
        <Button size="lg" iconRight={ArrowRight} onClick={() => navigate('/calibration/keyboard')} className="min-w-[280px]">
          I'm ready — let's start
        </Button>
      </div>
    </AssessmentShell>
  )
}
