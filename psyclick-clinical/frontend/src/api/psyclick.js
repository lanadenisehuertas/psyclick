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
        ...(sessionStorage.getItem('psyclick_token')
          ? { Authorization: `Bearer ${sessionStorage.getItem('psyclick_token')}` }
          : {}),
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
  setSession: (payload) => {
    if (payload?.token) sessionStorage.setItem('psyclick_token', payload.token)
    if (payload?.id) sessionStorage.setItem('psyclick_user', JSON.stringify({
      id: payload.id, name: payload.name, role: payload.role || 'clinician',
    }))
  },
  clearSession: () => {
    sessionStorage.removeItem('psyclick_token')
    sessionStorage.removeItem('psyclick_user')
  },
  // Auth
  login:            (id, password)        => post('/login',                   { id, password }),
  register:         (name, password, role = 'clinician') => post('/register', { name, password, role }),
  verifyClinician:  (id, password)        => post('/verify-clinician',        { id, password }),
  logout:           async () => {
    const result = await post('/logout', {})
    api.clearSession()
    return result
  },

  // Dashboard
  stats:            (clinician_id)        => get(`/stats${clinician_id ? `?clinician_id=${clinician_id}` : ''}`),
  recentSessions:   (clinician_id)        => get(`/sessions/recent${clinician_id ? `?clinician_id=${clinician_id}` : ''}`),

  // Clients
  clients:          (clinician_id)        => get(`/patients${clinician_id ? `?clinician_id=${clinician_id}` : ''}`),
  clientSessions:   (id)                  => get(`/patients/${id}/sessions`),
  sessionDetail:    (sid)                 => get(`/session/${sid}`),

  // Intake
  intakeStart:      (patient_id, clinician_id, consent, consent_version = '1.0') =>
    post('/intake/start', { patient_id, clinician_id, consent, consent_version }),

  // Auto-ID generation (clients only)
  nextClientId:     (clinician_id)        => get(`/next-client-id${clinician_id ? `?clinician_id=${clinician_id}` : ''}`),

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
  verifyAudit:      ()                    => get('/audit/verify'),

  // Delete
  deleteClient:     (id)                  => request(`/clients/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  // Export
  exportReport:     (report)              => post('/export/report',           { report }),
  exportSummary:    ()                    => post('/export/summary',          {}),
  createBackup:     ()                    => post('/admin/backup',            {}),
  verifyBackup:     (file, sha256)         => post('/admin/backup/verify',     { file, sha256 }),
  securityStatus:   ()                    => get('/admin/security-status'),
  users:            ()                    => get('/admin/users'),
  updateUser:       (id, role, status)     => request(`/admin/users/${id}`, {
    method: 'PATCH', body: JSON.stringify({ role, status }),
  }),

  // Normative baseline — read-only, pre-computed from 100-participant study population
  normativeStats:   ()                    => get('/normative/stats'),
  normativeCompare: (sessionId)           => get(`/normative/compare/${sessionId}`),

  syncStatus:       ()                    => get('/sync/status'),
  syncNow:          ()                    => post('/sync/now', {}),

  ping:             ()                    => get('/ping'),
  dbHealth:         ()                    => get('/db-health'),
}
