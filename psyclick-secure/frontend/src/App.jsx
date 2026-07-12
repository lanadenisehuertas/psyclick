import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppProvider, useApp } from './context/AppContext.jsx'
import Login               from './pages/Login.jsx'
import Dashboard           from './pages/Dashboard.jsx'
import Intake              from './pages/Intake.jsx'
import KeyboardCalibration from './pages/KeyboardCalibration.jsx'
import MouseCalibration    from './pages/MouseCalibration.jsx'
import PHQ9                from './pages/PHQ9.jsx'
import GAD7                from './pages/GAD7.jsx'
import EmotionalTask       from './pages/EmotionalTask.jsx'
import Report              from './pages/Report.jsx'
import Clients             from './pages/Patients.jsx'
import ClientDetail        from './pages/PatientDetail.jsx'
import Audit               from './pages/Audit.jsx'
import Landing             from './pages/Landing.jsx'
import SecurityCenter      from './pages/SecurityCenter.jsx'

function Guard({ children }) {
  const { user } = useApp()
  return user ? children : <Navigate to="/" replace />
}

function RoleGuard({ roles, children }) {
  const { user } = useApp()
  return user && roles.includes(user.role) ? children : <Navigate to="/dashboard" replace />
}

export default function App() {
  return (
    <AppProvider>
      <HashRouter>
        <Routes>
          <Route path="/landing"                       element={<Landing />} />
          <Route path="/"                              element={<Login />} />
          <Route path="/dashboard"                     element={<Guard><Dashboard /></Guard>} />
          <Route path="/intake"                        element={<Guard><Intake /></Guard>} />
          <Route path="/calibration/keyboard"          element={<Guard><KeyboardCalibration /></Guard>} />
          <Route path="/calibration/mouse"             element={<Guard><MouseCalibration /></Guard>} />
          <Route path="/assessment/phq9"               element={<Guard><PHQ9 /></Guard>} />
          <Route path="/assessment/gad7"               element={<Guard><GAD7 /></Guard>} />
          <Route path="/assessment/emotional"          element={<Guard><EmotionalTask /></Guard>} />
          <Route path="/report"                        element={<Guard><Report /></Guard>} />
          <Route path="/clients"                       element={<Guard><Clients /></Guard>} />
          <Route path="/clients/:clientId"             element={<Guard><ClientDetail /></Guard>} />
          <Route path="/clients/session/:sessionId"    element={<Guard><Report /></Guard>} />
          <Route path="/audit"                         element={<Guard><Audit /></Guard>} />
          <Route path="/security"                      element={<Guard><RoleGuard roles={['admin']}><SecurityCenter /></RoleGuard></Guard>} />
          {/* Normative tester portal removed — baseline pre-computed from 100-participant study population */}
          <Route path="/normative/*"                   element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </HashRouter>
    </AppProvider>
  )
}
