const BASE = 'http://127.0.0.1:5001/api'
const REQUEST_TIMEOUT_MS = 12000

async function request(path, options = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const res = await fetch(`${BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.headers || {}),
      },
    })
    const text = await res.text()
    let data = {}
    try {
      data = text ? JSON.parse(text) : {}
    } catch (_) {
      data = { success: false, error: text || 'Server returned an unreadable response.' }
    }
    if (!res.ok) {
      return {
        success: false,
        error: data.error || data.message || `Server error (${res.status}).`,
        ...data,
      }
    }
    return data
  } catch (err) {
    const offline = err?.name === 'AbortError'
      ? 'PsyClick API did not respond in time. Please restart the app or rebuild the packaged API.'
      : 'PsyClick API is not available. The packaged backend may have failed to start.'
    return { success: false, error: offline, detail: err?.message || String(err) }
  } finally {
    clearTimeout(timer)
  }
}

const post = (path, body) =>
  request(path, {
    method:  'POST',
    body:    JSON.stringify(body),
  })

const get = (path) => request(path)

export const api = {
  // Auth
  login:            (id, password)        => post('/login',                   { id, password }),
  register:         (name, password)      => post('/register',                { name, password }),
  verifyClinician:  (id, password)        => post('/verify-clinician',        { id, password }),
  logout:           ()                    => post('/logout',                  {}),

  // Dashboard
  stats:            (clinician_id)        => get(`/stats${clinician_id ? `?clinician_id=${clinician_id}` : ''}`),
  recentSessions:   (clinician_id)        => get(`/sessions/recent${clinician_id ? `?clinician_id=${clinician_id}` : ''}`),

  // Clients
  clients:          (clinician_id)        => get(`/patients${clinician_id ? `?clinician_id=${clinician_id}` : ''}`),
  clientSessions:   (id)                  => get(`/patients/${id}/sessions`),
  sessionDetail:    (sid)                 => get(`/session/${sid}`),

  // Intake
  intakeStart:      (patient_id, clinician_id) => post('/intake/start',       { patient_id, clinician_id }),

  // Auto-ID generation
  nextClientId:     (clinician_id)        => get(`/next-client-id${clinician_id ? `?clinician_id=${clinician_id}` : ''}`),
  nextTesterId:     ()                    => get('/next-tester-id'),

  // Calibration
  kCalStart:        ()                    => post('/calibration/keyboard/start', {}),
  kCalSave:         ()                    => post('/calibration/keyboard/save',  {}),
  mCalStart:        ()                    => post('/calibration/mouse/start',    {}),
  mCalSave:         ()                    => post('/calibration/mouse/save',     {}),

  // Assessment
  phqStart:         ()                    => post('/assessment/phq/start',    {}),
  phqSave:          (score)               => post('/assessment/phq/save',     { score }),
  gadStart:         ()                    => post('/assessment/gad/start',    {}),
  gadSave:          (score)               => post('/assessment/gad/save',     { score }),
  emotionalStart:   ()                    => post('/assessment/emotional/start', {}),
  questionSet:      (question)            => post('/assessment/question/set', { question }),
  wordBoxes:        (boxes)               => post('/assessment/word-boxes',   { boxes }),
  questionSnapshot: (question, response, qi, total) =>
                                             post('/assessment/question/snapshot', { question, response, qi, total }),
  assessmentFinish: ()                    => post('/assessment/finish',       {}),
  auditChoice:      (label, context)      => post('/assessment/audit/choice', { label, context }),
  auditIdle:        (context)             => post('/assessment/idle',         { context }),

  // Audit
  auditLogs:        (actor = 'clinician') => get(`/audit?actor=${actor}`),
  auditLog:         (actor, action, detail) => post('/audit/log',            { actor, action, detail }),

  // Delete
  deleteClient:     (id)                  => request(`/clients/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  // Export
  exportReport:     (report)              => post('/export/report',           { report }),
  exportSummary:    ()                    => post('/export/summary',          {}),

  // Normative baseline
  normativeLogin:   (tester_id, password) => post('/normative/login',        { tester_id, password }),
  normativeMode:    (active)              => post('/normative/mode',          { active }),
  normativeStats:   ()                    => get('/normative/stats'),
  normativeCompute: (id, password)        => post('/normative/compute',       { id, password }),
  normativeCompare: (sessionId)           => get(`/normative/compare/${sessionId}`),
  ping:             ()                    => get('/ping'),
  dbHealth:         ()                    => get('/db-health'),
}
