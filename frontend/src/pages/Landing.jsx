import {
  Activity,
  ArrowRight,
  BarChart3,
  Brain,
  Check,
  ChevronRight,
  Download,
  FileText,
  HeartPulse,
  Keyboard,
  Lock,
  MousePointer2,
  ShieldCheck,
  Sparkles,
  Users,
} from 'lucide-react'

const featureCards = [
  {
    icon: Keyboard,
    title: 'Keyboard calibration',
    text: 'Measures flight time, dwell time, typing velocity, error rate, and pauses so each session has a personal baseline.',
  },
  {
    icon: MousePointer2,
    title: 'Mouse dynamics',
    text: 'Tracks movement smoothness, cursor velocity, path entropy, jerk, and hesitation points during guided click tasks.',
  },
  {
    icon: HeartPulse,
    title: 'PHQ-9 and GAD-7',
    text: 'Adds standard depression and anxiety screening scores to every clinician-reviewed report.',
  },
  {
    icon: Brain,
    title: 'Emotional task',
    text: 'Uses 11 written prompts across 4 stressor domains to observe response rhythm, hesitation, and psychomotor shifts.',
  },
  {
    icon: BarChart3,
    title: 'Decision-support report',
    text: 'Summarizes GREEN, AMBER, and RED flags, T2, PSI, PAI, heatmaps, distributions, and recommendations.',
  },
  {
    icon: ShieldCheck,
    title: 'Audit and records',
    text: 'Supports session history, exports, client records, normative baselines, and clinician activity review.',
  },
]

const steps = [
  'Clinician signs in and starts intake',
  'Client confirms consent and completes calibration',
  'PHQ-9, GAD-7, and emotional prompts are completed',
  'PsyClick extracts psychomotor features',
  'Clinician reviews report, flags, and recommendations',
]

const algorithm = [
  ['1', 'Capture', 'Keystrokes, cursor movement, clicks, pauses, responses, and screening answers.'],
  ['2', 'Smooth', 'Mouse paths use a 5-point weighted moving average to reduce noise while preserving hesitation patterns.'],
  ['3', 'Extract', 'Keyboard and mouse biomarkers become an 8-feature psychomotor vector.'],
  ['4', 'Compare', 'EWMA baseline and Hotelling T2 detect multivariate shifts from the user’s own calibration.'],
  ['5', 'Classify', 'PSI, PAI, and fuzzy rules map patterns into GREEN, AMBER, or RED decision-support flags.'],
]

function ProductMockup() {
  return (
    <div className="landing-device">
      <div className="device-topbar">
        <span />
        <span />
        <span />
      </div>
      <div className="device-content">
        <div className="device-sidebar">
          <img src="/images/LOGOggg.png" alt="" />
          <div className="device-pill active" />
          <div className="device-pill" />
          <div className="device-pill" />
        </div>
        <div className="device-main">
          <div className="device-header">
            <div>
              <p>Clinical overview</p>
              <h3>PsyClick Session</h3>
            </div>
            <span>GREEN</span>
          </div>
          <div className="device-grid">
            <div className="device-stat">
              <small>PHQ-9</small>
              <strong>7</strong>
            </div>
            <div className="device-stat">
              <small>GAD-7</small>
              <strong>5</strong>
            </div>
            <div className="device-stat teal">
              <small>PSI</small>
              <strong>0.82</strong>
            </div>
          </div>
          <div className="heatmap-preview">
            {Array.from({ length: 42 }).map((_, i) => (
              <i key={i} style={{ '--d': `${(i % 7) * 0.04}s` }} />
            ))}
          </div>
          <div className="rhythm-lines">
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Landing() {
  return (
    <main className="landing-page">
      <nav className="landing-nav">
        <a className="landing-brand" href="#top">
          <img src="/images/LOGO WITH WORD.png" alt="PsyClick" />
        </a>
        <div className="landing-links">
          <a href="#features">Features</a>
          <a href="#guide">Guide</a>
          <a href="#algorithm">Algorithm</a>
          <a href="#team">Team</a>
        </div>
        <a className="nav-cta" href="#download">
          <Download size={17} />
          Download
        </a>
      </nav>

      <section id="top" className="hero-section">
        <div className="organic organic-one" />
        <div className="organic organic-two" />
        <div className="hero-copy">
          <span className="eyebrow"><Sparkles size={15} /> Calmer clinical screening</span>
          <h1>PsyClick</h1>
          <p className="hero-lede">
            A welcoming desktop companion for psychomotor screening, emotional tasks, and clinician-ready reports.
          </p>
          <div className="hero-actions">
            <a className="landing-btn primary" href="#download">
              Download PsyClick <ArrowRight size={18} />
            </a>
            <a className="landing-btn secondary" href="#guide">
              View usage guide <ChevronRight size={18} />
            </a>
          </div>
          <div className="hero-trust">
            <span><Check size={15} /> PHQ-9 + GAD-7</span>
            <span><Check size={15} /> PSI + PAI biomarkers</span>
            <span><Check size={15} /> Clinician reviewed</span>
          </div>
        </div>
        <div className="hero-visual">
          <ProductMockup />
          <div className="floating-card card-one">
            <Activity size={20} />
            <div><strong>Hotelling T2</strong><span>Baseline-aware anomaly review</span></div>
          </div>
          <div className="floating-card card-two">
            <FileText size={20} />
            <div><strong>Report ready</strong><span>Exportable clinician summary</span></div>
          </div>
        </div>
      </section>

      <section className="purpose-band">
        <div>
          <p className="section-kicker">Purpose</p>
          <h2>Designed to make screening feel clear, structured, and human.</h2>
        </div>
        <p>
          PsyClick combines standard questionnaires with typing rhythm, cursor dynamics, hesitation patterns, and emotional response tasks. The result is a decision-support report that helps clinicians review psychomotor slowing, agitation, and follow-up needs with more context.
        </p>
      </section>

      <section className="role-section">
        <div className="role-card patient">
          <span>For clients and patients</span>
          <h3>Simple guided tasks, no right or wrong answers.</h3>
          <p>Clients type naturally, click naturally, answer PHQ-9 and GAD-7 honestly, and respond to prompts while their clinician guides the session.</p>
        </div>
        <div className="role-card clinician">
          <span>For clinicians</span>
          <h3>A complete workflow from intake to export.</h3>
          <p>Clinicians can manage sessions, review flags, compare against baselines, inspect heatmaps, export reports, and revisit client history.</p>
        </div>
      </section>

      <section id="features" className="feature-section">
        <div className="section-heading">
          <p className="section-kicker">Feature Tour</p>
          <h2>Everything the app does, presented with intention.</h2>
        </div>
        <div className="feature-grid">
          {featureCards.map((feature) => {
            const Icon = feature.icon
            return (
              <article className="feature-card" key={feature.title}>
                <span className="feature-icon"><Icon size={23} /></span>
                <h3>{feature.title}</h3>
                <p>{feature.text}</p>
              </article>
            )
          })}
        </div>
      </section>

      <section id="guide" className="guide-section">
        <div className="guide-copy">
          <p className="section-kicker">Usage Guide</p>
          <h2>One calm path through the full PsyClick session.</h2>
          <p>
            The landing page should make instructions clear for every user: clinicians lead the workflow, clients complete guided tasks, and normative testers contribute authorized baseline sessions.
          </p>
        </div>
        <div className="journey">
          {steps.map((step, index) => (
            <div className="journey-step" key={step}>
              <span>{String(index + 1).padStart(2, '0')}</span>
              <p>{step}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="algorithm" className="algorithm-section">
        <div className="section-heading">
          <p className="section-kicker">Behind the Signals</p>
          <h2>The algorithm explained without losing people.</h2>
        </div>
        <div className="algorithm-flow">
          {algorithm.map(([number, title, text]) => (
            <article key={title}>
              <span>{number}</span>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="download" className="download-section">
        <div>
          <p className="section-kicker">Download</p>
          <h2>PsyClick for Windows</h2>
          <p>First public PsyClick release. Direct Windows installer access for approved PsyClick deployment.</p>
        </div>
        <a className="landing-btn primary dark" href="/downloads/PsyClick-Setup.exe">
          <Download size={19} /> Download installer
        </a>
      </section>

      <section id="team" className="team-section">
        <div className="team-photo">
          <Users size={44} />
          <span>Team photo placeholder</span>
        </div>
        <div>
          <p className="section-kicker">Our Team</p>
          <h2>Built by ByteMe.</h2>
          <p>Add the final team photo, member names, roles, contact details, and adviser or organization details directly in Vercel before launch.</p>
          <div className="team-tags">
            <span>Product</span>
            <span>Clinical workflow</span>
            <span>Frontend</span>
            <span>Psychomotor algorithms</span>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <img src="/images/LOGO WITH WORD white.png" alt="PsyClick" />
        <p>PsyClick is a decision-support tool. It does not replace clinical judgment, diagnosis, emergency assessment, or clinic protocols.</p>
        <span>© 2026 PsyClick by ByteMe</span>
      </footer>
    </main>
  )
}
