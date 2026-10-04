import { createContext, useCallback, useContext, useState } from 'react'

const Ctx = createContext(null)

function readJSON(key) {
  try { return JSON.parse(sessionStorage.getItem(key) || 'null') } catch (_) { return null }
}

export function AppProvider({ children }) {
  const [user, setUserState] = useState(() => readJSON('psyclick_user'))
  const setUser = useCallback((value) => {
    setUserState(value)
    if (value) sessionStorage.setItem('psyclick_user', JSON.stringify(value))
    else {
      sessionStorage.removeItem('psyclick_user')
      sessionStorage.removeItem('psyclick_token')
      sessionStorage.removeItem('psyclick_client')
    }
  }, [])

  // The client being assessed survives a page reload during the assessment
  const [client, setClientState] = useState(() => readJSON('psyclick_client'))
  const setClient = useCallback((value) => {
    setClientState(value)
    if (value) sessionStorage.setItem('psyclick_client', JSON.stringify(value))
    else sessionStorage.removeItem('psyclick_client')
  }, [])

  const [report,     setReport]     = useState(null)      // full report object
  const [phqScore,   setPhqScore]   = useState(0)
  const [gadScore,   setGadScore]   = useState(0)

  return (
    <Ctx.Provider value={{
      user, setUser,
      client, setClient,
      report, setReport,
      phqScore, setPhqScore,
      gadScore, setGadScore,
    }}>
      {children}
    </Ctx.Provider>
  )
}

export const useApp = () => useContext(Ctx)
