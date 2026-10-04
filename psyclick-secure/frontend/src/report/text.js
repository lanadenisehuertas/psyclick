// Plain-language vocabulary and recommendation rules for the assessment report.

export const DOMAIN_NAMES = { 1: 'Time & workload', 2: 'Relationships', 3: 'Performance', 4: 'Self-image' }
export const LEVEL_NAMES  = { A: 'Mild', B: 'Moderate', C: 'Strong' }
export const ITEM9_LABEL  = { 1: 'Several days', 2: 'More than half the days', 3: 'Nearly every day' }

export const DOMAIN_TIPS = {
  1: 'Deadlines, workload and routines.',
  2: 'Conflict, closeness and being let down or left out.',
  3: 'Exams, presentations and being evaluated.',
  4: 'How the client sees themselves on hard days.',
}

// Healthy reference values (p75 / p95) used when no percentile is available
export const HEALTHY_REF = { psi: { p75: 9.32, p95: 29.63 }, pai: { p75: 15.55, p95: 80.26 } }
// Healthy adults' average gap between key presses (middle half, seconds)
export const HEALTHY_GAP = { p25: 0.118, p50: 0.168, p75: 0.201 }

// Minimal clinically important differences used for "meaningful change"
export const MCID = { phq: 5, gad: 4 }   // Löwe et al. 2004; Toussaint et al. 2020

export function phqLabel(s) {
  return s <= 4 ? 'Minimal' : s <= 9 ? 'Mild' : s <= 14 ? 'Moderate' : s <= 19 ? 'Moderately severe' : 'Severe'
}
export function gadLabel(s) {
  return s <= 4 ? 'Minimal' : s <= 9 ? 'Mild' : s <= 14 ? 'Moderate' : 'Severe'
}

export const GLOSSARY = {
  T2: {
    title: 'Overall behaviour change (Hotelling T²)',
    what: "How far the client's typing and mouse rhythm moved from their own calm warm-up while answering the emotional prompts.",
    flag: 'The green zone is where 95 of 100 healthy adults fall. Above it means a larger shift than most healthy people show.',
    how: 'Multivariate distance from the within-session baseline: T² = Δxᵀ·S⁻¹·Δx. Cut-offs are Harrell-Davis estimates from 83 healthy adults.',
  },
  PSI: {
    title: 'Slowing (Psychomotor Slowing Index)',
    what: 'Slower key presses, longer key holds and more pauses than during the warm-up.',
    flag: 'Read against healthy adults: above the 85th percentile is worth noting, above the 95th is marked.',
    how: 'Sum of T² contributions from flight time, dwell time and pause frequency where they increased (Mason & Young, 2002).',
  },
  PAI: {
    title: 'Restlessness (Psychomotor Agitation Index)',
    what: 'More irregular mouse movement, faster corrections and more errors than during the warm-up.',
    flag: 'Read against healthy adults: above the 85th percentile is worth noting, above the 95th is marked.',
    how: 'Sum of T² contributions from path entropy, jerk, error rate, cursor velocity and typing velocity in the agitation direction.',
  },
  Trace: {
    title: 'Session trace',
    what: 'Each dot is one written prompt, in the order the client answered them.',
    flag: 'Dots above the shaded band changed more than in 95% of healthy adults on a single prompt. Look for where the line rises, not single dots.',
    how: 'Per-prompt T² against the warm-up baseline; band = healthy single-prompt 95th percentile.',
  },
  Reading: {
    title: 'Where attention lingered',
    what: 'While reading each prompt, the cursor often rests near the words a person is dwelling on.',
    flag: 'Darker words held the cursor longer. Words that stand out in emotional prompts are good, concrete starting points for conversation.',
    how: 'Mouse stillness of 100 ms or more over a word, summed per word (each stop capped at 5 s). It is a proxy for attention, not eye tracking.',
  },
  Grid: {
    title: 'Topic × strength map',
    what: 'The same prompts grouped by topic (rows) and by how emotionally strong the prompt was (columns).',
    flag: 'A row that is darker overall points to a topic worth exploring. Darker towards the right means the reaction grew with emotional load.',
    how: 'Average of the prompts in each cell. Empty cells have no prompt of that kind.',
  },
  Rhythm: {
    title: 'Typing rhythm',
    what: 'How long the client waited between key presses while writing.',
    flag: 'Most healthy adults average 0.12–0.20 s between keys. A long tail to the right means frequent pauses.',
    how: 'All key-to-key gaps from the written answers, grouped into 50 ms bins. Gaps over 1 s are collected in the last bar.',
  },
}

// Recommendations stay within what a screening result can support: they
// suggest what to look at next, they do not diagnose.
export function clinicalRecs({ flag, label = '', psi = 0, pai = 0, phq = 0, gad = 0, domainT2 = {}, levelT2 = {}, itemP95 = Infinity, item9 = 0 }) {
  const recs = []
  if (item9 > 0) {
    recs.push({ tone: 'coral', title: 'Suicide-risk assessment in this session',
      desc: `PHQ-9 question 9 was answered “${ITEM9_LABEL[item9]}”. Use a structured tool such as the C-SSRS, document the outcome and follow your safety-planning protocol before the client leaves.` })
  }

  if (flag === 'RED') {
    recs.push({ tone: 'coral', title: 'Review today',
      desc: `Behaviour changed far more than in healthy adults. Together with PHQ-9 ${phq} (${phqLabel(phq).toLowerCase()}) and GAD-7 ${gad} (${gadLabel(gad).toLowerCase()}), discuss the result with the client in this session.` })
  } else if (flag === 'AMBER' && label !== 'Insufficient Data') {
    recs.push({ tone: 'amber', title: 'Follow up within 48–72 hours',
      desc: 'Behaviour changed more than in most healthy adults. Use the topic map to choose what to explore first.' })
  } else if (label === 'Insufficient Data') {
    recs.push({ tone: 'amber', title: 'Repeat the behavioural part',
      desc: 'Too little typing was captured to compare with the warm-up. The questionnaire scores are still valid.' })
  } else {
    recs.push({ tone: 'teal', title: 'Continue routine care',
      desc: 'Behaviour stayed within the healthy range during the emotional prompts.' })
  }

  const flagged = flag === 'RED' || flag === 'AMBER'
  if (flagged && label !== 'Insufficient Data') {
    if (label.includes('Retardation') || psi > pai * 1.3) {
      recs.push({ tone: 'teal', title: 'Ask about slowing and energy',
        desc: 'Slowing dominated the change. Consider exploring energy, fatigue and slowed thinking — for example MADRS items 6–7.' })
    } else if (label.includes('Agitation') || pai > psi * 1.3) {
      recs.push({ tone: 'teal', title: 'Ask about restlessness and tension',
        desc: 'Restlessness dominated the change. Consider exploring tension, sleep onset and concentration — for example HAM-A items 1–4.' })
    } else if (label.includes('Mixed')) {
      recs.push({ tone: 'teal', title: 'Both slowing and restlessness rose',
        desc: 'Both indices increased together. Consider a broader mood history, including any periods of unusually high energy.' })
    }
  }

  if (phq >= 15) {
    recs.push({ tone: 'amber', title: phq >= 20 ? 'Severe depressive symptoms reported' : 'Moderately severe depressive symptoms reported',
      desc: `PHQ-9 ${phq}/27. A structured clinical evaluation is indicated.` })
  }
  if (gad >= 10) {
    recs.push({ tone: 'amber', title: gad >= 15 ? 'Severe anxiety symptoms reported' : 'Moderate anxiety symptoms reported',
      desc: `GAD-7 ${gad}/21. Consider a fuller anxiety assessment and discuss treatment options.` })
  }

  const dom = Object.entries(domainT2)
  if (flagged && dom.length) {
    const [gid, val] = dom.reduce((b, c) => Number(c[1]) > Number(b[1]) ? c : b)
    if (Number(val) > itemP95) {
      recs.push({ tone: 'teal', title: `Start with “${DOMAIN_NAMES[Number(gid)]}”`,
        desc: `Prompts about ${DOMAIN_NAMES[Number(gid)].toLowerCase()} produced the largest change. ${DOMAIN_TIPS[Number(gid)]}` })
    }
  }

  const la = levelT2.A || 0, lb = levelT2.B || 0, lc = levelT2.C || 0
  if (lc > lb && lb > la && lc > itemP95) {
    recs.push({ tone: 'teal', title: 'Reaction grew with emotional load',
      desc: 'Change rose from mild to strong prompts. The strong prompts are the most useful entry points for discussion.' })
  } else if (la > lc && la > itemP95) {
    recs.push({ tone: 'teal', title: 'Already activated at the start',
      desc: 'Change was highest on the mildest prompts. Ask about stressors before the session.' })
  }
  return recs
}
