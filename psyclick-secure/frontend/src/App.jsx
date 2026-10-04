import { useEffect } from 'react'
import { HashRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { MotionConfig } from 'motion/react'
import { AppProvider, useApp } from './context/AppContext.jsx'
import { ToastProvider } from './components/ui.jsx'
import Login               from './pages/Login.jsx'
import Dashboard           from './pages/Dashboard.jsx'
import Intake              from './pages/Intake.jsx'
import Welcome             from './pages/AssessmentWelcome.jsx'
import KeyboardCalibration from './pages/KeyboardCalibration.jsx'
import MouseCalibration    from './pages/MouseCalibration.jsx'
import PHQ9                from './pages/PHQ9.jsx'
import GAD7                from './pages/GAD7.jsx'
import EmotionalTask       from './pages/EmotionalTask.jsx'
import AssessmentDone      from './pages/AssessmentDone.jsx'
import Report              from './pages/Report.jsx'
import Clients             from './pages/Patients.jsx'
import ClientDetail        from './pages/PatientDetail.jsx'
import Audit               from './pages/Audit.jsx'
import Landing             from './pages/Landing.jsx'
import SecurityCenter      from './pages/SecurityCenter.jsx'

import { HOME_FOR_ROLE } from './lib/roles.js'

function Guard({ children }) {
  const { user } = useApp()
  return user ? children : <Navigate to="/" replace />
}

function RoleGuard({ roles, children }) {
  const { user } = useApp()
  if (!user) return <Navigate to="/" replace />
  return roles.includes(user.role) ? children : <Navigate to={HOME_FOR_ROLE[user.role] || '/dashboard'} replace />
}

const CLINICAL = ['admin', 'clinician']

// Sends the user back to sign-in when the server reports an expired login.
function SessionWatcher() {
  const { setUser } = useApp()
  const navigate = useNavigate()
  useEffect(() => {
    function onExpired() {
      setUser(null)
      navigate('/', { replace: true, state: { reason: 'expired' } })
    }
    window.addEventListener('psyclick:session-expired', onExpired)
    return () => window.removeEventListener('psyclick:session-expired', onExpired)
  }, [setUser, navigate])
  return null
}

function Clinical({ children }) {
  return <RoleGuard roles={CLINICAL}>{children}</RoleGuard>
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <AppProvider>
        <ToastProvider>
          <HashRouter>
            <SessionWatcher />
            <Routes>
              <Route path="/landing"                    element={<Landing />} />
              <Route path="/"                           element={<Login />} />
              <Route path="/dashboard"                  element={<Clinical><Dashboard /></Clinical>} />
              <Route path="/intake"                     element={<Clinical><Intake /></Clinical>} />
              <Route path="/assessment/welcome"         element={<Clinical><Welcome /></Clinical>} />
              <Route path="/calibration/keyboard"       element={<Clinical><KeyboardCalibration /></Clinical>} />
              <Route path="/calibration/mouse"          element={<Clinical><MouseCalibration /></Clinical>} />
              <Route path="/assessment/phq9"            element={<Clinical><PHQ9 /></Clinical>} />
              <Route path="/assessment/gad7"            element={<Clinical><GAD7 /></Clinical>} />
              <Route path="/assessment/emotional"       element={<Clinical><EmotionalTask /></Clinical>} />
              <Route path="/assessment/done"            element={<Clinical><AssessmentDone /></Clinical>} />
              <Route path="/report"                     element={<Clinical><Report /></Clinical>} />
              <Route path="/clients"                    element={<Clinical><Clients /></Clinical>} />
              <Route path="/clients/:clientId"          element={<Clinical><ClientDetail /></Clinical>} />
              <Route path="/clients/session/:sessionId" element={<Clinical><Report /></Clinical>} />
              <Route path="/audit"                      element={<RoleGuard roles={['admin', 'auditor']}><Audit /></RoleGuard>} />
              <Route path="/security"                   element={<RoleGuard roles={['admin']}><SecurityCenter /></RoleGuard>} />
              <Route path="/normative/*"                element={<Navigate to="/dashboard" replace />} />
              <Route path="*"                           element={<Guard><Navigate to="/dashboard" replace /></Guard>} />
            </Routes>
          </HashRouter>
        </ToastProvider>
      </AppProvider>
    </MotionConfig>
  )
}
